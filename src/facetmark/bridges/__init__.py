"""Adapters that let other people's applications use this ranking.

Each module here implements someone else's plugin contract. The rule for this
package: no feature lives here that the host application already ships. The
point of a bridge is to stop reimplementing crawlers, extensions and UIs.
"""
