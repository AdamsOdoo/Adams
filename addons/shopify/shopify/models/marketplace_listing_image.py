import base64
import logging
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter

from odoo import models, fields, api
from odoo.addons.base_marketplace.models.misc import guess_mimetype
from odoo.addons.shopify.models.graphql_queries import STAGED_UPLOADS_CREATE
from odoo.addons.shopify.models.misc import upload_content_to_staged_target

_logger = logging.getLogger("Qamah:Shopify")

# Task: T7609 - One chunk is read, staged and uploaded as a unit. Kept small on purpose: the parent
# prepares the next chunk while the current one uploads, so only two chunks of bytes are ever in memory.
SHOPIFY_STAGED_MEDIA_BATCH = 200
SHOPIFY_STAGED_MEDIA_WORKERS = 8

# Task: T7609 - Every upload thread keeps its own session, so the TLS handshake to the bucket is paid
# once per thread for the whole staging instead of once per image.
_staged_upload_state = threading.local()


def _shopify_staged_upload_session():
    """
    Task: T7609 - Session of the calling upload thread, created on first use.
    Returns:
        requests.Session: Connection pool reused by every upload this thread performs.
    """
    session = getattr(_staged_upload_state, 'session', None)
    if session is None:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=SHOPIFY_STAGED_MEDIA_WORKERS, pool_maxsize=SHOPIFY_STAGED_MEDIA_WORKERS)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        _staged_upload_state.session = session
    return session


class ListingImage(models.Model):
    _inherit = 'mk.listing.image'

    shopify_alt_text = fields.Char("Shopify Alt text")
    media_id = fields.Char("Media Identification", copy=False)

    # To consider image as a new image remove media_id when change image.
    @api.onchange('url')
    def _onchange_url(self):
        previous_url = self._origin.url
        current_url = self.url
        if self.url and previous_url != current_url:
            self.media_id = False
        res = super(ListingImage, self)._onchange_url()
        return res

    def _shopify_media_source(self):
        """
        Task: T7609 - URL Shopify must download this image from.
        Returns the staged Shopify link when the running operation staged this image (see
        :meth:`_shopify_stage_media`), and the Odoo image route otherwise - single-product flows, which
        create no burst, and images whose staged upload was refused.
        Returns:
            str: Source URL to send as `originalSource` / `mediaSrc`.
        """
        self.ensure_one()
        return self.env.context.get('shopify_staged_media', {}).get(self.id) or self.url

    def _shopify_staged_media_filename(self, mimetype):
        """
        Task: T7609 - Name the staged file, because Shopify keeps it as the name of the media it creates.
        Args:
            mimetype (str): Mimetype detected from the image binary.
        Returns:
            str: Record name reduced to safe characters, carrying the extension of ``mimetype``.
        """
        self.ensure_one()
        extension = mimetype.split('/')[-1]
        if extension == 'svg+xml':
            extension = 'svg'
        safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', self.name or '').strip('._-')
        return f"{safe_name or f'image_{self.id}'}.{extension}"

    def _shopify_request_staged_targets(self, mk_instance_id, upload_vals):
        """
        Task: T7609 - Ask Shopify for one signed upload target per image of a batch.
        Args:
            mk_instance_id (record): Instance whose credentials request the targets.
            upload_vals (list): Dicts carrying the ``filename``, ``mimetype`` and ``content`` of each image.
        Returns:
            list: Staged targets, positionally matching ``upload_vals``, or an empty list when the batch
                could not be staged - the caller then keeps the Odoo image URL for those images.
        """
        variables = {'input': [{
            # fileSize must be the exact byte count: Shopify signs a content-length-range policy from it,
            # and GCS refuses the upload with EntityTooLarge when the bytes do not fit the signed bound.
            'resource': 'IMAGE', 'filename': vals['filename'], 'mimeType': vals['mimetype'],
            'httpMethod': 'POST', 'fileSize': str(len(vals['content'])),
        } for vals in upload_vals]}
        try:
            res = mk_instance_id.execute_graphql_query(STAGED_UPLOADS_CREATE, variables)
        except Exception as e:
            _logger.warning("STAGE MEDIA: staged upload request failed (%s); this batch keeps its Odoo image URL.", e)
            return []

        staged_data = ((res or {}).get('data') or {}).get('stagedUploadsCreate') or {}
        user_errors = staged_data.get('userErrors', [])
        if user_errors:
            _logger.warning("STAGE MEDIA: stagedUploadsCreate errors: %s", user_errors)
            return []

        targets = staged_data.get('stagedTargets') or []
        if len(targets) != len(upload_vals):
            # Targets are paired with images by position, so a short list would store the bytes of one
            # image under the key signed for another. Drop the whole batch instead of mixing them up.
            _logger.warning("STAGE MEDIA: Shopify returned %s targets for %s images; this batch keeps its Odoo image URL. Response: %s", len(targets), len(upload_vals), res)
            return []
        return targets

    def _shopify_read_image_binaries(self, image_ids):
        """
        Task: T7609 - Read the binary of a chunk of images in one pass.
        ``image.image`` is an attachment field: reading it record by record costs one query and one
        filestore read each, and hands the bytes back base64 encoded only for the caller to decode them
        again. The attachments of the whole chunk are read in a single search instead, and their raw
        bytes are used as they are.
        Args:
            image_ids (list): Ids of the images whose binary is needed.
        Returns:
            dict: {mk.listing.image id: bytes}. An image holding no binary is absent from the mapping.
        """
        contents = {}
        attachments = self.env['ir.attachment'].sudo().search([('res_model', '=', self._name), ('res_field', '=', 'image'), ('res_id', 'in', image_ids)])
        for attachment in attachments:
            if attachment.raw:
                contents[attachment.res_id] = attachment.raw
        # Images whose binary is not stored as an attachment still go through the ORM.
        for image in self.browse([image_id for image_id in image_ids if image_id not in contents]):
            if image.image:
                contents[image.id] = base64.b64decode(image.image)
        return contents

    def _shopify_prepare_staged_chunk(self, mk_instance_id, chunk_groups):
        """
        Task: T7609 - Read the bytes of one chunk and ask Shopify for the target of each of its images.
        Args:
            mk_instance_id (record): Instance whose credentials request the targets.
            chunk_groups (list): Lists of image ids, one list per distinct binary, first id is the one
                whose bytes and name are sent.
        Returns:
            list: (vals, target) pairs ready to upload, empty when the chunk could not be staged - its
                images then keep their Odoo image URL.
        """
        leader_ids = [group[0] for group in chunk_groups]
        contents = self._shopify_read_image_binaries(leader_ids)
        groups_by_leader = {group[0]: group for group in chunk_groups}
        upload_vals = []
        # One recordset for the whole chunk: `name` is then read for every image in a single query.
        for image in self.browse(leader_ids):
            content = contents.get(image.id)
            if not content:
                continue
            mimetype = guess_mimetype(content, default='image/png')
            upload_vals.append({'images': groups_by_leader[image.id], 'content': content, 'mimetype': mimetype, 'filename': image._shopify_staged_media_filename(mimetype)})

        if not upload_vals:
            return []
        targets = self._shopify_request_staged_targets(mk_instance_id, upload_vals)
        if not targets:
            return []
        return list(zip(upload_vals, targets))

    def _shopify_stage_media(self, mk_instance_id):
        """
        Task: T7609 - Upload the images of ``self`` to Shopify's own storage and return the URL Shopify
        must read each one from.

        A bulk payload makes Shopify download every `originalSource` concurrently. Pointing those at the
        Odoo image route puts thousands of parallel requests on this server, and the hosting front sheds
        part of them with HTTP 429 - Shopify then marks the media FAILED with "The file does not exist
        (Unsuccessful HTTP response code: 429)". Staging reverses the direction: Odoo pushes the bytes to
        the Google Cloud Storage bucket Shopify signed for it, and the payload carries a Shopify link, so
        no image request reaches Odoo at all.

        Images holding the same binary (``image_hex``) are uploaded once and share one staged link.

        Args:
            mk_instance_id (record): Instance whose credentials request the staged targets.
        Returns:
            dict: {mk.listing.image id: staged resourceUrl}. An image that could not be staged is absent
                from the mapping, so the caller keeps sending its Odoo URL for that one.
        """
        staged_url_by_image_id = {}
        images_by_content = OrderedDict()
        if not self:
            return staged_url_by_image_id
        # Task: T7609 - Read the hex of every image in one query. Grouping them through the ORM would
        # evaluate `image.image` record by record, and that binary is an attachment: an export carrying
        # thousands of images would then load every blob from the filestore only to test that it exists.
        self.env.flush_all()
        self.env.cr.execute("""
            SELECT id, image_hex
              FROM mk_listing_image
             WHERE id IN %s
               AND image_hex IS NOT NULL
          ORDER BY id
        """, (tuple(self.ids),))
        for image_id, image_hex in self.env.cr.fetchall():
            images_by_content.setdefault(image_hex, []).append(image_id)

        def _upload_staged_media(pair):
            """Push one image to its target; runs in a thread, so it must stay free of ORM access."""
            vals, target = pair
            error_message = upload_content_to_staged_target(target, vals['content'], vals['filename'], vals['mimetype'], "STAGE MEDIA", session=_shopify_staged_upload_session())
            # The bytes are of no use once the bucket holds them; dropping them here keeps the memory of
            # a chunk bounded by what is still in flight rather than by the whole chunk.
            vals['content'] = b''
            return vals, target, error_message

        content_groups = list(images_by_content.values())
        chunks = [content_groups[index:index + SHOPIFY_STAGED_MEDIA_BATCH] for index in range(0, len(content_groups), SHOPIFY_STAGED_MEDIA_BATCH)]
        prepare_seconds = upload_seconds = 0.0
        # Task: T7609 - One executor for the whole staging: its threads - and the session each one keeps -
        # stay alive across chunks. The bytes and the targets of the next chunk are prepared while the
        # uploads of the current one are still running, so the read and the stagedUploadsCreate call of a
        # chunk no longer sit idle between two batches of uploads.
        with ThreadPoolExecutor(max_workers=SHOPIFY_STAGED_MEDIA_WORKERS) as executor:
            uploading = None
            for chunk_index in range(len(chunks) + 1):
                started_at = time.time()
                prepared = self._shopify_prepare_staged_chunk(mk_instance_id, chunks[chunk_index]) if chunk_index < len(chunks) else []
                prepare_seconds += time.time() - started_at

                # executor.map submits every upload immediately, so this chunk is already on its way while
                # the results of the previous one are collected below.
                submitted = executor.map(_upload_staged_media, prepared) if prepared else None
                started_at = time.time()
                for vals, target, error_message in uploading or []:
                    if error_message:
                        _logger.warning(error_message)
                        continue
                    resource_url = target.get('resourceUrl', '')
                    if not resource_url:
                        _logger.warning("STAGE MEDIA: no resourceUrl returned for %s; it keeps its Odoo image URL.", vals['filename'])
                        continue
                    for image_id in vals['images']:
                        staged_url_by_image_id[image_id] = resource_url
                upload_seconds += time.time() - started_at
                uploading = submitted

        _logger.info("STAGE MEDIA: staged %s of %s image(s) on Shopify for instance %s (%s distinct binaries in %s chunk(s); prepare %.1fs, upload %.1fs).",
                     len(staged_url_by_image_id), len(self), mk_instance_id.name, len(content_groups), len(chunks), prepare_seconds, upload_seconds)
        return staged_url_by_image_id
