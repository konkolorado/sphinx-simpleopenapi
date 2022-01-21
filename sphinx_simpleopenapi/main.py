import typing as t

from docutils import nodes
from docutils.statemachine import ViewList
from pkg_resources import get_distribution
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles
from sphinxcontrib.autohttp.common import http_directive

from sphinx_simpleopenapi.errors import UndefinedSecurityScheme
from sphinx_simpleopenapi.utils import get_openapi_spec


class SimpleOpenApi(SphinxDirective):
    has_content = True
    required_arguments = 1

    @property
    def api_spec(self) -> t.Dict[str, t.Any]:
        _, abs_path = self.env.relfn2path(self.arguments[0])
        return get_openapi_spec(abs_path, "utf-8")

    def _string_for_param(self, *, type: str, name: str, description: str) -> str:
        if type == "query":
            return f"   :query {name}: {description}"
        if type == "path":
            return f"   :param {name}: {description}"
        return ""

    def _string_for_security(self, *, description: str) -> str:
        return f"   :reqheader Authorization: {description}"

    def _string_for_response(self, *, code: int, description: str) -> str:
        return f"   :statuscode {code}: {description}"

    def get_params(self, body: t.Dict[str, t.Any]) -> t.Set[str]:
        query_params = set()
        parameters: t.List[dict] = body.get("parameters", [])
        for parameter_def in parameters:
            p_type = parameter_def["in"]
            p_name = parameter_def["name"]
            p_description = parameter_def["description"]
            p_line = self._string_for_param(
                type=p_type, name=p_name, description=p_description
            )
            query_params.add(p_line)
        return query_params

    def get_security_scheme_definitions(self) -> t.Dict[str, t.Any]:
        return self.api_spec.get("components", {}).get("securitySchemes", {})

    def get_global_security(self) -> t.List[dict]:
        return self.api_spec.get("security", [])

    def get_method_security(self, body: t.Dict[str, t.Any]):
        defined_schemes = self.get_security_scheme_definitions()
        global_security_schemes = self.get_global_security()
        method_security_schemes = body.get("security", [])

        all_schemes = dict()
        for scheme_dict in method_security_schemes + global_security_schemes:
            scheme_name = list(scheme_dict.keys())[0]
            scheme_scopes = scheme_dict[scheme_name]

            if scheme_name not in defined_schemes:
                raise UndefinedSecurityScheme(
                    f"Scheme {scheme_name} is used but was never defined."
                )

            if scheme_name not in all_schemes:
                all_schemes[scheme_name] = scheme_scopes
            else:
                all_schemes[scheme_name].extend(scheme_scopes)

        for scheme, scopes in all_schemes.items():
            s_description = defined_schemes[scheme].get("description", scheme_name)
            yield self._string_for_security(
                description=f"{s_description}. Required OAuth2 scopes: {', '.join(scopes)}."
            )

    def get_responses(self, body: t.Dict[str, t.Any]):
        responses = body.get("responses", {})
        for response_code, response_body in responses.items():
            description = response_body.get("description", "")
            yield self._string_for_response(code=response_code, description=description)

    def make_rst(self):
        for path_name, path_body in self.api_spec["paths"].items():
            params = self.get_params(path_body)
            for method_name, method_body in path_body.items():
                if method_name == "parameters":
                    continue
                if method_body.get("deprecated", False):
                    continue

                method_description = method_body.get("description")
                for line in http_directive(method_name, path_name, method_description):
                    yield line
                for line in self.get_method_security(method_body):
                    yield line
                for line in sorted(params):
                    yield line
                for line in self.get_responses(method_body):
                    yield line

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, "<simpleopenapi>")
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app: Sphinx):
    # Plug into httpdomain
    app.setup_extension("sphinxcontrib.httpdomain")

    app.add_directive("simpleopenapi", SimpleOpenApi)
    return {
        "version": get_distribution("sphinx_simpleopenapi").version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
