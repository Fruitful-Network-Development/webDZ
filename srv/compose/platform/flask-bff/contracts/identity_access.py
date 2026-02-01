"""Interface stubs for identity access contract data."""


class IdentityAccessContract:
    """Describe identity access request/response shapes.

    Intended inputs:
        - subject identifiers (e.g., user/service IDs)
        - requested scopes/permissions
        - optional context (tenant, environment, request metadata)

    Intended outputs:
        - access decision (allow/deny)
        - granted scopes/permissions
        - optional audit metadata and reason codes

    TODO:
        - Define expected fields for subject identifiers.
        - Define allowed permission/scope values.
        - Define audit metadata structure.
    """

    def evaluate_access(self, subject, requested_scopes, context=None):
        """Evaluate access for a subject.

        Args:
            subject: Subject identifier input (TODO: specify fields).
            requested_scopes: Collection of requested scopes (TODO: define type).
            context: Optional request context (TODO: specify fields).

        Returns:
            Access decision payload (TODO: define fields).
        """
        raise NotImplementedError
