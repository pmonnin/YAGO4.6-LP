from concurrent.futures import ThreadPoolExecutor, as_completed

import argparse
import matplotlib.pyplot
import seaborn
import tqdm

from utils import yago_utils
from utils.logging_utils import get_logger
from utils.yago_utils import get_yago_endpoint, compute_node_degree, get_target_nodes


def main():
    parser = argparse.ArgumentParser(prog="get_target_nodes_degree_distribution",
                                     description="Get the degree distribution of target nodes based on the provided shape")
    parser.add_argument("--shape-uri", dest="shape_uri", help="Shape URI", required=True)
    parser.add_argument("--yago-url", dest="yago_url", help="YAGO SPARQL endpoint URL", type=str,
                        default=None)
    parser.add_argument("-l,--log-level", dest="log_level", help="Set the logging level", type=str,
                        default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--output-hist", dest="output_hist", help="Output file for histogram plot",
                        required=True)
    parser.add_argument("--output-ecdf", dest="output_ecdf", help="Output file for ECDF plot",
                        required=True)
    args = parser.parse_args()

    logger = get_logger(args.log_level)

    logger.info("get_target_nodes_degree_distribution: start")
    logger.info(f"SPARQL endpoint: {args.yago_url if args.yago_url is not None else yago_utils.YAGO_ENDPOINT}")
    logger.info(f"Shape URI: {args.shape_uri}")
    logger.info(f"Output histogram: {args.output_hist}")
    logger.info(f"Output ECDF: {args.output_ecdf}")

    yago_endpoint = get_yago_endpoint(args.yago_url)

    target_node_degrees = []

    try:
        logger.info("Getting target nodes...")
        target_nodes = get_target_nodes(args.shape_uri, args.yago_url)
        logger.info(f"Number of target nodes: {len(target_nodes)}")

        logger.info("Computing node degrees (multithreaded)...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(compute_node_degree, n, args.yago_url): n
                for n in target_nodes
            }

            for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
                target_node_degrees.append(future.result())

    except Exception as e:
        print(e)

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

    matplotlib.pyplot.tight_layout()
    matplotlib.pyplot.savefig(args.output_hist, format="pdf")
    matplotlib.pyplot.close()

    # ECDF
    matplotlib.pyplot.figure(figsize=(9, 5), layout="constrained")

    seaborn.ecdfplot(
        target_node_degrees,
        complementary=True,
        log_scale=(True, True),
    )

    matplotlib.pyplot.xlabel("Node degree")
    matplotlib.pyplot.ylabel("P(Degree ≥ x) (log scale)")
    matplotlib.pyplot.title("CCDF of Node Degrees (log scale)")

    matplotlib.pyplot.tight_layout()
    matplotlib.pyplot.savefig(args.output_ecdf, format="pdf")
    matplotlib.pyplot.close()

    logger.info("get_target_nodes_degree_distribution: done")


if __name__ == '__main__':
    main()
