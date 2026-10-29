import SPARQLWrapper

YAGO_ENDPOINT = "https://yago-knowledge.org/sparql/qlever"

# Predicates that are not relations between entities, and thus do not count in node degrees
DEGREE_EXCLUDED_PREDICATES = [
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "http://www.w3.org/2002/07/owl#sameAs",
]

SPARQL_PREFIXES = """
    PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
    PREFIX sh:<http://www.w3.org/ns/shacl#>
"""


def target_nodes_pattern(node_var: str, shape_uri: str) -> str:
    """
        Return the SPARQL triple pattern matching the target nodes of a given SHACL shape in YAGO.

        YAGO node shapes are also classes and declare no explicit target, so their target
        nodes are the instances of the class with the same URI, including instances of its
        subclasses (SHACL implicit class targets). This is the only place where this
        definition is written; queries on target nodes must use it.

        :param node_var: The SPARQL variable bound to target nodes (e.g. "?targetNode").
        :type node_var: str
        :param shape_uri: The URI of the SHACL shape.
        :type shape_uri: str
        :return: The triple pattern, to be included in a WHERE clause using SPARQL_PREFIXES.
        :rtype: str
    """
    return f"{node_var} rdf:type/rdfs:subClassOf* <{shape_uri}> ."


def get_yago_endpoint(url: str | None = None) -> SPARQLWrapper.SPARQLWrapper:
    """
        Create and return a SPARQLWrapper endpoint configured for the YAGO knowledge graph.

        The returned endpoint is preconfigured with:
        - the given SPARQL endpoint URL, or the YAGO public SPARQL endpoint URL if none is given
        - JSON as the return format

        A new SPARQLWrapper instance is created on each call, making this function
        safe to use in multithreaded contexts (the endpoint object is not shared
        across threads).

        :param url: SPARQL endpoint URL to use. Defaults to the YAGO public SPARQL endpoint if None.
        :type url: str | None
        :return: A configured SPARQLWrapper instance ready for queries
        :rtype: SPARQLWrapper.SPARQLWrapper
    """
    yago_endpoint = SPARQLWrapper.SPARQLWrapper(
        url if url is not None else YAGO_ENDPOINT
    )
    yago_endpoint.setReturnFormat(SPARQLWrapper.JSON)
    return yago_endpoint


def get_node_shapes(url: str | None = None) -> list[str]:
    """
        Retrieve all SHACL node shapes defined in YAGO.

        A new SPARQLWrapper endpoint is created within the function to ensure thread safety.

        :param url: SPARQL endpoint URL to use. Defaults to the YAGO public SPARQL endpoint if None.
        :type url: str | None
        :return: The sorted list of node shape URIs (sorted so that it does not depend on the endpoint).
        :rtype: list[str]
        :raises SPARQLWrapper.SPARQLExceptions: If the SPARQL query fails, or the endpoint is unreachable.
    """
    yago_endpoint = get_yago_endpoint(url)

    yago_endpoint.setQuery(f"""
        {SPARQL_PREFIXES}
        SELECT DISTINCT ?shape
        WHERE
        {{
            ?shape rdf:type sh:NodeShape .
        }}
    """)

    results = yago_endpoint.queryAndConvert()
    return sorted(r["shape"]["value"] for r in results["results"]["bindings"])


def count_target_nodes(shape_uri: str, url: str | None = None) -> int:
    """
        Count the target nodes of a given SHACL shape in YAGO, without retrieving them.

        A new SPARQLWrapper endpoint is created within the function to ensure thread safety.

        :param shape_uri: The URI of the SHACL shape whose target nodes are counted.
        :type shape_uri: str
        :param url: SPARQL endpoint URL to use. Defaults to the YAGO public SPARQL endpoint if None.
        :type url: str | None
        :return: The number of target nodes of the given shape.
        :rtype: int
        :raises SPARQLWrapper.SPARQLExceptions: If the SPARQL query fails, or the endpoint is unreachable.
    """
    yago_endpoint = get_yago_endpoint(url)

    yago_endpoint.setQuery(f"""
        {SPARQL_PREFIXES}
        SELECT (COUNT(DISTINCT ?targetNode) AS ?targetNodes)
        WHERE
        {{
            {target_nodes_pattern("?targetNode", shape_uri)}
        }}
    """)

    results = yago_endpoint.queryAndConvert()
    return int(results["results"]["bindings"][0]["targetNodes"]["value"])


def get_target_nodes(shape_uri: str, url: str | None = None) -> list[str]:
    """
        Retrieve all target nodes that are instances of a given SHACL shape in YAGO.

        This function queries the YAGO SPARQL endpoint for all target nodes of the
        provided shape (see target_nodes_pattern). Each node URI is collected into a
        list and returned.

        A new SPARQLWrapper endpoint is created within the function to ensure thread safety.

        :param shape_uri: The URI of the SHACL shape for which target nodes are retrieved.
        :type shape_uri: str
        :param url: SPARQL endpoint URL to use. Defaults to the YAGO public SPARQL endpoint if None.
        :type url: str | None
        :return: A list of node URIs that are instances of the given shape.
        :rtype: list[str]
        :raises SPARQLWrapper.SPARQLExceptions: If the SPARQL query fails, or the endpoint is unreachable.
    """

    yago_endpoint = get_yago_endpoint(url)
    target_nodes = []

    yago_endpoint.setQuery(f"""
        {SPARQL_PREFIXES}
        SELECT DISTINCT ?targetNode 
        WHERE
        {{
            {target_nodes_pattern("?targetNode", shape_uri)}
        }}
    """)

    results = yago_endpoint.queryAndConvert()
    for r in results["results"]["bindings"]:
        target_nodes.append(r["targetNode"]["value"])

    return target_nodes


def compute_target_nodes_degrees(shape_uri: str, url: str | None = None) -> dict[str, int]:
    """
        Compute the total degree of all target nodes of a given SHACL shape in YAGO.

        The degree of a node counts both its outgoing and incoming edges. Outgoing edges
        are triples where the node is the subject, and incoming edges are triples where
        the node is the object. Only edges pointing to or coming from other URIs are
        counted, not literals. Edges whose predicate is in DEGREE_EXCLUDED_PREDICATES
        (rdf:type, owl:sameAs) are not counted either.

        Degrees are computed with two aggregate queries (outgoing and incoming edges)
        for all target nodes at once.

        A new SPARQLWrapper endpoint is created within the function to ensure thread safety.

        :param shape_uri: The URI of the SHACL shape whose target nodes degrees are computed.
        :type shape_uri: str
        :param url: SPARQL endpoint URL to use. Defaults to the YAGO public SPARQL endpoint if None.
        :type url: str | None
        :return: A dictionary mapping each target node URI to its degree (0 for target nodes without counted edges).
        :rtype: dict[str, int]
        :raises SPARQLWrapper.SPARQLExceptions: If the SPARQL queries fail, or the endpoint is unreachable.
    """
    endpoint = get_yago_endpoint(url)
    excluded_predicates = ", ".join(f"<{p}>" for p in DEGREE_EXCLUDED_PREDICATES)

    degrees = {n: 0 for n in get_target_nodes(shape_uri, url)}

    # Outgoing edges
    endpoint.setQuery(f"""
        {SPARQL_PREFIXES}
        SELECT ?targetNode (COUNT(*) AS ?degree)
        WHERE {{
            SELECT DISTINCT ?targetNode ?p ?o
            WHERE {{
                {target_nodes_pattern("?targetNode", shape_uri)}
                ?targetNode ?p ?o .
                FILTER(ISURI(?o)) .
                FILTER(?p NOT IN ({excluded_predicates})) .
            }}
        }}
        GROUP BY ?targetNode
    """)
    results = endpoint.queryAndConvert()
    for r in results["results"]["bindings"]:
        degrees[r["targetNode"]["value"]] += int(r["degree"]["value"])

    # Incoming edges
    endpoint.setQuery(f"""
        {SPARQL_PREFIXES}
        SELECT ?targetNode (COUNT(*) AS ?degree)
        WHERE {{
            SELECT DISTINCT ?targetNode ?s ?p
            WHERE {{
                {target_nodes_pattern("?targetNode", shape_uri)}
                ?s ?p ?targetNode .
                FILTER(?p NOT IN ({excluded_predicates})) .
            }}
        }}
        GROUP BY ?targetNode
    """)
    results = endpoint.queryAndConvert()
    for r in results["results"]["bindings"]:
        degrees[r["targetNode"]["value"]] += int(r["degree"]["value"])

    return degrees
