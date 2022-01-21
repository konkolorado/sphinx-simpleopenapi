from sphinx.errors import SphinxError


class ApiSpecNotFound(SphinxError):
    category = "OpenApi Spec Missing"


class UndefinedSecurityScheme(SphinxError):
    category = "Undefined Security Scheme Referenced"
