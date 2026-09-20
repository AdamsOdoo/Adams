# Disposable integration fixtures only; never install in a customer database.


def post_init_hook(env):
    """Prepare the bilingual disposable environment before post-install tests."""
    languages = env['res.lang'].with_context(active_test=False).search([
        ('code', 'in', ['en_US', 'ar_001']), ('active', '=', False),
    ])
    if languages:
        env['base.language.install'].create({
            'lang_ids': [(6, 0, languages.ids)],
            'overwrite': False,
        }).lang_install()
