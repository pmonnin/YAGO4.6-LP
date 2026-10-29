import rdflib
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, SH

THING = rdflib.URIRef("http://schema.org/Thing")


def load_schema(schema_path: str) -> rdflib.Graph:
    """
    Load the YAGO schema (node shapes, property shapes and their class hierarchy).

    The schema is read from a local file rather than from the YAGO SPARQL endpoint,
    because the blank nodes of the sh:or lists are not preserved on the endpoint.

    :param schema_path: Path to the YAGO schema file in Turtle format.
    :return: The schema graph.
    """
    return rdflib.Graph().parse(schema_path, format="turtle")


def get_property_ranges(schema: rdflib.Graph, property_shape: rdflib.term.Node) -> set[rdflib.URIRef]:
    """
    Return the classes allowed as values of a property shape.

    Classes are given either directly by sh:class, or by the sh:class of the
    alternatives of an sh:or list. Datatype properties have no range class.

    :param schema: The schema graph.
    :param property_shape: The property shape.
    :return: The set of range classes (empty for datatype properties).
    """
    ranges = set(schema.objects(property_shape, SH["class"]))

    for alternatives in schema.objects(property_shape, SH["or"]):
        for alternative in Collection(schema, alternatives):
            ranges.update(schema.objects(alternative, SH["class"]))

    return ranges


def get_superclasses(schema: rdflib.Graph, shape: rdflib.URIRef) -> set[rdflib.URIRef]:
    """
    Return the direct and indirect superclasses of a shape in the schema.

    :param schema: The schema graph.
    :param shape: The shape (also a class in YAGO).
    :return: The set of direct and indirect superclasses, without the shape itself.
    """
    superclasses = set()
    to_visit = [shape]

    while to_visit:
        for superclass in schema.objects(to_visit.pop(), RDFS.subClassOf):
            if superclass not in superclasses:
                superclasses.add(superclass)
                to_visit.append(superclass)

    return superclasses


def get_declared_links(schema: rdflib.Graph) -> dict[str, dict[str, int]]:
    """
    Compute, for each node shape, the links to other shapes declared in the schema.

    Object properties of a shape are its property shapes with range classes, declared
    on the shape or inherited from its superclasses. The properties of schema:Thing
    (e.g. yago:follows, yago:partOf) are inherited by every shape and do not
    characterize any of them, so they are left out.

    For a shape S:
    - "object_properties" is the number of distinct paths of its object properties
    - "linked_to_shapes" is the number of distinct shapes, other than S and schema:Thing,
      found in the ranges of its object properties
    - "linked_from_shapes_strict" is the number of distinct other shapes having an object
      property whose range necessarily contains instances of S: S itself or one of its
      subclasses
    - "linked_from_shapes_possible" is the number of distinct other shapes having an object
      property whose range may contain instances of S: S itself, one of its subclasses, or
      one of its superclasses other than schema:Thing. Such links are allowed but not
      required, so this is an upper bound. YAGO mostly declares ranges on broad classes
      (e.g. schema:Organization), so the strict count is 0 for many specific shapes

    :param schema: The schema graph.
    :return: A dictionary mapping each node shape URI to its declared link counts.
    """
    shapes = set(schema.subjects(RDF.type, SH.NodeShape))
    superclasses = {s: get_superclasses(schema, s) - {THING} for s in shapes}
    subclasses = {s: {o for o in shapes if s in superclasses[o]} for s in shapes}

    # Object properties declared on each shape: path -> range classes
    own_properties = {}
    for s in shapes:
        own_properties[s] = {}
        if s == THING:
            continue
        for property_shape in schema.objects(s, SH.property):
            ranges = get_property_ranges(schema, property_shape)
            if ranges:
                path = schema.value(property_shape, SH.path)
                own_properties[s].setdefault(path, set()).update(ranges)

    # Object properties of each shape, including inherited ones: path -> range classes
    properties = {}
    for s in shapes:
        properties[s] = {}
        for c in {s} | superclasses[s]:
            for path, ranges in own_properties.get(c, {}).items():
                properties[s].setdefault(path, set()).update(ranges)

    def get_linking_shapes(s: rdflib.URIRef, linked_ranges: set[rdflib.URIRef]) -> set[rdflib.URIRef]:
        # Shapes other than s having an object property with a range in linked_ranges
        return {o for o in shapes if o != s and any(r & linked_ranges for r in properties[o].values())}

    links = {}
    for s in shapes:
        ranges = set().union(*properties[s].values())
        links[str(s)] = {
            "object_properties": len(properties[s]),
            "linked_to_shapes": len(ranges - {s, THING}),
            "linked_from_shapes_strict": len(get_linking_shapes(s, {s} | subclasses[s])),
            "linked_from_shapes_possible": len(get_linking_shapes(s, {s} | subclasses[s] | superclasses[s])),
        }

    return links
