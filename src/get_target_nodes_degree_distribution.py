import argparse
import matplotlib.pyplot
import seaborn
import sys

from utils import yago_utils
from utils.logging_utils import get_logger
from utils.yago_utils import compute_target_nodes_degrees


def main():
    parser = argparse.ArgumentParser(prog="get_target_nodes_degree_distribution",
                                     description="Get the degree distribution of target nodes based on the provided shape")
    parser.add_argument("--shape-uri", dest="shape_uri", help="Shape URI", required=True)
    parser.add_argument("--yago-url", dest="yago_url", help="YAGO SPARQL endpoint URL", type=str,
                        default=None)
    parser.add_argument("-l", "--log-level", dest="log_level", help="Set the logging level", type=str,
                        default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--output-hist", dest="output_hist", help="Output file for histogram plot",
                        required=True)
    parser.add_argument("--output-ccdf", dest="output_ccdf", help="Output file for CCDF plot",
                        required=True)
    args = parser.parse_args()

    logger = get_logger(args.log_level)

    logger.info("get_target_nodes_degree_distribution: start")
    logger.info(f"SPARQL endpoint: {args.yago_url if args.yago_url is not None else yago_utils.YAGO_ENDPOINT}")
    logger.info(f"Shape URI: {args.shape_uri}")
    logger.info(f"Output histogram: {args.output_hist}")
    logger.info(f"Output CCDF: {args.output_ccdf}")

    try:
        logger.info("Computing target nodes degrees...")
        degrees = compute_target_nodes_degrees(args.shape_uri, args.yago_url)
        logger.info(f"Number of target nodes: {len(degrees)}")

    except Exception as e:
        # Do not plot partial degrees that would look like the full distribution
        logger.error(f"Querying YAGO failed, no output written: {e}")
        sys.exit(1)

    # Degree 0 cannot be shown on log scales
    target_node_degrees = [d for d in degrees.values() if d > 0]
    logger.info(f"Number of target nodes with degree 0 (not plotted): {len(degrees) - len(target_node_degrees)}")

    seaborn.set_theme(
        style="whitegrid",
        context="talk",   # bigger fonts
        palette="viridis"
    )

    # Histogram
    matplotlib.pyplot.figure(figsize=(9, 5), layout="constrained")
    seaborn.histplot(
        target_node_degrees,
        bins="auto",      # smart binning
        kde=True,
        stat="count",
        edgecolor="white",
        linewidth=1,
        log_scale=(True, True),
    )

    matplotlib.pyplot.xlabel("Node degree (log scale)")
    matplotlib.pyplot.ylabel("Count")
    matplotlib.pyplot.title("Distribution of Node Degrees (log scale)")

    matplotlib.pyplot.savefig(args.output_hist, format="pdf")
    matplotlib.pyplot.close()

    # CCDF
    matplotlib.pyplot.figure(figsize=(9, 5), layout="constrained")

    seaborn.ecdfplot(
        target_node_degrees,
        complementary=True,
        log_scale=(True, True),
    )

    matplotlib.pyplot.xlabel("Node degree")
    matplotlib.pyplot.ylabel("P(Degree ≥ x) (log scale)")
    matplotlib.pyplot.title("CCDF of Node Degrees (log scale)")

    matplotlib.pyplot.savefig(args.output_ccdf, format="pdf")
    matplotlib.pyplot.close()

    logger.info("get_target_nodes_degree_distribution: done")


if __name__ == '__main__':
    main()
