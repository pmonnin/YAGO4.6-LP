import argparse
import csv
import tqdm

from utils import yago_utils
from utils.logging_utils import get_logger
from utils.yago_utils import get_yago_endpoint


def main():
    parser = argparse.ArgumentParser(prog="get_shapes_info", description="Get shapes and number of target nodes")
    parser.add_argument("--output", dest="output", help="Output file", required=True)
    parser.add_argument("--yago-url", dest="yago_url", help="YAGO SPARQL endpoint URL", type=str,
                        default=None)
    parser.add_argument("-l,--log-level", dest="log_level", help="Set the logging level", type=str,
                        default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    args = parser.parse_args()

    logger = get_logger(args.log_level)

    logger.info("get_shapes_info: start")
    logger.info(f"SPARQL endpoint: {args.yago_url if args.yago_url is not None else yago_utils.YAGO_ENDPOINT}")
    logger.info(f"Output file: {args.output}")

    yago_endpoint = get_yago_endpoint(args.yago_url)

    shapes = []

    try:
        yago_endpoint.setQuery("""
            PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?shape
            WHERE
            {
                ?shape rdf:type <http://www.w3.org/ns/shacl#NodeShape> .
            }
            """)

        results = yago_endpoint.queryAndConvert()

        for r in results["results"]["bindings"]:
            shapes.append([r["shape"]["value"], 0])

        logger.info(f"Number of shapes: {len(shapes)}")

        for s in tqdm.tqdm(shapes):
            yago_endpoint.setQuery(f"""
                PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
                SELECT (COUNT(DISTINCT ?s) AS ?targetNodes) 
                WHERE
                {{
                    ?s rdf:type/rdfs:subClassOf* <{s[0]}> .
                }}
            """)

            results = yago_endpoint.queryAndConvert()
            s[1] = results["results"]["bindings"][0]["targetNodes"]["value"]

    except Exception as e:
        print(e)

    with open(args.output, 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(["Shape", "# target nodes"])
        csvwriter.writerows(shapes)

    logger.info("get_shapes_info: done")


if __name__ == '__main__':
    main()
