import SPARQLWrapper

YAGO_ENDPOINT = "https://yago-knowledge.org/sparql/qlever"

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


def compute_node_degree(node_uri: str, url: str | None = None) -> int:
    """
        Compute the total degree of a node in the YAGO knowledge graph.

        This function counts both outgoing and incoming edges of the given node URI.
        Outgoing edges are triples where the node is the subject, and incoming edges
        are triples where the node is the object. Only edges pointing to or coming
        from other URIs are counted, not literals.

        A new SPARQLWrapper endpoint is created for each call, making this function
        safe to use in multithreaded contexts.

        :param node_uri: The URI of the node whose degree is to be computed.
        :type node_uri: str
        :param url: SPARQL endpoint URL to use. Defaults to the YAGO public SPARQL endpoint if None.
        :type url: str | None
        :return: The total degree of the node (number of incoming + outgoing edges).
        :rtype: int
        :raises SPARQLWrapper.SPARQLExceptions: If there is an error executing the SPARQL queries.
    """
    endpoint = get_yago_endpoint(url)

    degree = 0

    # Outgoing edges
    endpoint.setQuery(f"""
        SELECT DISTINCT ?p ?o
        WHERE {{
            <{node_uri}> ?p ?o .
            FILTER(ISURI(?o)) .
        }}
    """)
    results = endpoint.queryAndConvert()
    degree += len(results["results"]["bindings"])

    # Incoming edges
    endpoint.setQuery(f"""
        SELECT DISTINCT ?s ?p
        WHERE {{
            ?s ?p <{node_uri}> .
        }}
    """)
    results = endpoint.queryAndConvert()
    degree += len(results["results"]["bindings"])

    return degree


def get_target_nodes(shape_uri: str, url: str | None = None) -> list[str]:
    """
        Retrieve all target nodes that are instances of a given SHACL shape in YAGO.

        This function queries the YAGO SPARQL endpoint for all nodes whose type
        matches or is a subclass of the provided shape URI. Each node URI is collected
        into a list and returned.

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
        PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?targetNode 
        WHERE
        {{
            ?targetNode rdf:type/rdfs:subClassOf* <{shape_uri}> .
        }}
    """)

    results = yago_endpoint.queryAndConvert()
    for r in results["results"]["bindings"]:
        target_nodes.append(r["targetNode"]["value"])

    return target_nodes
