import argparse
import pickle
import random

from utils import yago_utils
from utils.logging_utils import get_logger
from utils.yago_utils import compute_node_degree, get_target_nodes


def main():
    parser = argparse.ArgumentParser(prog="get_seed_nodes", description="Get seed nodes based on the provided shape, "
                                                                       "the number of seed nodes and the min degree")
    parser.add_argument("--shape-uri", dest="shape_uri", help="Shape URI", required=True)
    parser.add_argument("--seed-nodes", dest="seed_nodes_number", help="Number of seed nodes to sample",
                        type=int, required=True)
    parser.add_argument("--min-degree", dest="min_degree", help="Minimum degree of target nodes", type=int,
                        required=True)
    parser.add_argument("--output", dest="output", help="Output file to save seed nodes", required=True)
    parser.add_argument("--yago-url", dest="yago_url", help="YAGO SPARQL endpoint URL", type=str,
                        default=None)
    parser.add_argument("-l,--log-level", dest="log_level", help="Set the logging level", type=str,
                        default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    args = parser.parse_args()

    logger = get_logger(args.log_level)

    logger.info("get_seed_nodes: start")
    logger.info(f"SPARQL endpoint: {args.yago_url if args.yago_url is not None else yago_utils.YAGO_ENDPOINT}")
    logger.info(f"Shape URI: {args.shape_uri}")
    logger.info(f"Seed nodes number: {args.seed_nodes_number}")
    logger.info(f"Minimum degree: {args.min_degree}")
    logger.info(f"Output file: {args.output}")

    seed_nodes = []

    try:
        # Get all target nodes of the given shape
        logger.info("Getting target nodes...")
        target_nodes = get_target_nodes(args.shape_uri, args.yago_url)
        logger.info(f"Number of target nodes: {len(target_nodes)}")

        # Shuffle and take the first N seed nodes
        logger.info("Selecting seed nodes...")
        random.shuffle(target_nodes)
        while len(seed_nodes) < args.seed_nodes_number and target_nodes:
            n = target_nodes.pop()
            degree = compute_node_degree(n, args.yago_url)

            if degree >= args.min_degree:
                seed_nodes.append(n)
                logger.debug(f"Seed node added ({len(seed_nodes)} / {args.seed_nodes_number})")
            else:
                logger.debug("Seed node rejected due to low degree")

        logger.info(f"Number of randomly selected seed nodes: {len(seed_nodes)}")
        logger.debug(f"Seed nodes: {seed_nodes}")

    except Exception as e:
        print(e)

    # Save seed nodes
    logger.info("Saving seed nodes")
    with open(args.output, 'wb') as f:
        pickle.dump(seed_nodes, f)

    logger.info("get_seed_nodes: done")


if __name__ == '__main__':
    main()
