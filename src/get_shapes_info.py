import argparse
import csv
import json
import statistics
import sys
import tqdm

from utils import yago_utils
from utils.logging_utils import get_logger
from utils.schema_utils import get_declared_links, load_schema
from utils.yago_utils import count_target_nodes, get_node_shapes, get_nodes_predicates_edges, get_random_target_nodes

CSV_HEADER = [
    "Shape",
    "# target nodes",
    "# declared object properties",
    "# declared linked to shapes",
    "# declared linked from shapes (strict)",
    "# declared linked from shapes (possible)",
    "Sample size",
    "Median outgoing edges",
    "P90 outgoing edges",
    "Median incoming edges",
    "P90 incoming edges",
    "# frequent outgoing predicates",
    "# frequent incoming predicates",
]


def get_sample_statistics(sample: list[str], url: str | None, min_predicate_share: float) -> list:
    """
    Compute the statistics of the edges of the sampled target nodes of a shape
    :param sample: the sampled target nodes
    :param url: SPARQL endpoint URL to use (YAGO public SPARQL endpoint if None)
    :param min_predicate_share: minimum share of sampled nodes using a predicate for it to be frequent
    :return: the sample size, median and 90th percentile of outgoing and incoming edges per node, and numbers of
        frequent outgoing and incoming predicates (empty values for an empty sample)
    """
    if not sample:
        return [0] + [""] * 6

    outgoing, incoming = get_nodes_predicates_edges(sample, url)
    row = [len(sample)]

    # Medians and percentiles rather than means, as degrees are heavy-tailed
    for edges in (outgoing, incoming):
        degrees = [sum(edges[n].values()) for n in sample]
        p90 = statistics.quantiles(degrees, n=10, method="inclusive")[8] if len(degrees) > 1 else degrees[0]
        row += [statistics.median(degrees), p90]

    for edges in (outgoing, incoming):
        predicate_nodes = {}
        for n in sample:
            for p in edges[n]:
                predicate_nodes[p] = predicate_nodes.get(p, 0) + 1
        row.append(sum(1 for c in predicate_nodes.values() if c / len(sample) >= min_predicate_share))

    return row


def main():
    parser = argparse.ArgumentParser(prog="get_shapes_info", description="Get shapes, their number of target nodes, "
                                                                        "their declared links to other shapes, and "
                                                                        "statistics on the edges of a sample of their "
                                                                        "target nodes")
    parser.add_argument("--output", dest="output", help="Output file", required=True)
    parser.add_argument("--schema", dest="schema", help="Local YAGO schema file (Turtle)", required=True)
    parser.add_argument("--sample-size", dest="sample_size", help="Number of target nodes sampled for each shape",
                        type=int, default=1000)
    parser.add_argument("--min-predicate-share", dest="min_predicate_share", help="Minimum share of sampled target "
                        "nodes using a predicate for it to be counted as frequent", type=float, default=0.01)
    parser.add_argument("--output-sample", dest="output_sample", help="Output file to save the sampled target nodes "
                        "(JSON)", default=None)
    parser.add_argument("--input-sample", dest="input_sample", help="Previously saved sampled target nodes (JSON) to "
                        "use instead of sampling new ones", default=None)
    parser.add_argument("--yago-url", dest="yago_url", help="YAGO SPARQL endpoint URL", type=str,
                        default=None)
    parser.add_argument("-l", "--log-level", dest="log_level", help="Set the logging level", type=str,
                        default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    args = parser.parse_args()

    logger = get_logger(args.log_level)

    logger.info("get_shapes_info: start")
    logger.info(f"SPARQL endpoint: {args.yago_url if args.yago_url is not None else yago_utils.YAGO_ENDPOINT}")
    logger.info(f"Schema file: {args.schema}")
    logger.info(f"Sample size: {args.sample_size}")
    logger.info(f"Minimum predicate share: {args.min_predicate_share}")
    logger.info(f"Input sample file: {args.input_sample}")
    logger.info(f"Output sample file: {args.output_sample}")
    logger.info(f"Output file: {args.output}")

    logger.info("Computing declared links from the schema...")
    declared_links = get_declared_links(load_schema(args.schema))

    samples = {}
    if args.input_sample is not None:
        logger.info("Loading sampled target nodes...")
        with open(args.input_sample) as f:
            samples = json.load(f)

    rows = []

    try:
        logger.info("Getting node shapes...")
        shapes = get_node_shapes(args.yago_url)
        logger.info(f"Number of shapes: {len(shapes)}")

        logger.info("Counting target nodes of each shape...")
        for s in tqdm.tqdm(shapes):
            rows.append([s, count_target_nodes(s, args.yago_url)])

    except Exception as e:
        # Do not write partial results that would look like valid counts
        logger.error(f"Querying YAGO failed, no output written: {e}")
        sys.exit(1)

    for row in rows:
        if row[0] in declared_links:
            links = declared_links[row[0]]
            row += [links["object_properties"], links["linked_to_shapes"], links["linked_from_shapes_strict"],
                    links["linked_from_shapes_possible"]]
        else:
            logger.warning(f"Shape not found in the schema file: {row[0]}")
            row += [""] * 4

    logger.info("Computing statistics on sampled target nodes...")
    for row in tqdm.tqdm(rows):
        try:
            if row[0] not in samples:
                samples[row[0]] = get_random_target_nodes(row[0], args.sample_size, args.yago_url)
            row += get_sample_statistics(samples[row[0]], args.yago_url, args.min_predicate_share)

        except Exception as e:
            # Leave the statistics of this shape empty rather than failing for all shapes
            logger.warning(f"Sample statistics failed for {row[0]}, left empty: {e}")
            row += [""] * 7

    if args.output_sample is not None:
        logger.info("Saving sampled target nodes...")
        with open(args.output_sample, 'w') as f:
            json.dump(samples, f, indent=2, sort_keys=True)

    with open(args.output, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(CSV_HEADER)
        csvwriter.writerows(rows)

    logger.info("get_shapes_info: done")


if __name__ == '__main__':
    main()
