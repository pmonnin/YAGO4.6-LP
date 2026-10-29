import argparse
import csv
import sys
import tqdm

from utils import yago_utils
from utils.logging_utils import get_logger
from utils.yago_utils import count_target_nodes, get_node_shapes


def main():
    parser = argparse.ArgumentParser(prog="get_shapes_info", description="Get shapes and number of target nodes")
    parser.add_argument("--output", dest="output", help="Output file", required=True)
    parser.add_argument("--yago-url", dest="yago_url", help="YAGO SPARQL endpoint URL", type=str,
                        default=None)
    parser.add_argument("-l", "--log-level", dest="log_level", help="Set the logging level", type=str,
                        default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    args = parser.parse_args()

    logger = get_logger(args.log_level)

    logger.info("get_shapes_info: start")
    logger.info(f"SPARQL endpoint: {args.yago_url if args.yago_url is not None else yago_utils.YAGO_ENDPOINT}")
    logger.info(f"Output file: {args.output}")

    shapes = []

    try:
        logger.info("Getting node shapes...")
        shapes = [[shape, 0] for shape in get_node_shapes(args.yago_url)]
        logger.info(f"Number of shapes: {len(shapes)}")

        logger.info("Counting target nodes of each shape...")
        for s in tqdm.tqdm(shapes):
            s[1] = count_target_nodes(s[0], args.yago_url)

    except Exception as e:
        # Do not write partial results that would look like valid counts
        logger.error(f"Querying YAGO failed, no output written: {e}")
        sys.exit(1)

    with open(args.output, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(["Shape", "# target nodes"])
        csvwriter.writerows(shapes)

    logger.info("get_shapes_info: done")


if __name__ == '__main__':
    main()
