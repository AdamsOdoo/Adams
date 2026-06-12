# Simulator Guide

## Internal-Only Status

`shopify_simulator` is internal QA tooling only. It must not ship in the public Odoo App Store package for Shopify Connector Pro Ultimate Edition.

## Existing Simulator References

- `addons/shopify_simulator/doc/DESIGN.md`
- `addons/shopify_simulator/doc/shopify_simulator_user_guide.md`

## Testing Rule

The simulator may fake Shopify responses, webhooks, throttling, and error modes. It must not fake, bypass, or replace production connector logic.
