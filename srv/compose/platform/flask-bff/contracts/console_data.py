"""Interface stubs for console data contract data."""


class ConsoleDataContract:
    """Describe console data retrieval shapes.

    Intended inputs:
        - console identifiers (user, tenant, environment)
        - requested data domains (dashboards, widgets, metrics)
        - optional filters, pagination, or time ranges

    Intended outputs:
        - data payloads for requested domains
        - pagination metadata
        - optional aggregation metadata

    TODO:
        - Define data domain identifiers.
        - Define filter and pagination structures.
        - Define payload schema for each domain.
    """

    def fetch_console_data(self, console_id, domains=None, filters=None, context=None):
        """Fetch console data.

        Args:
            console_id: Console identifier input (TODO: specify fields).
            domains: Optional list of data domains to retrieve.
            filters: Optional filters/pagination (TODO: define fields).
            context: Optional request context (TODO: specify fields).

        Returns:
            Console data payload (TODO: define fields).
        """
        raise NotImplementedError
