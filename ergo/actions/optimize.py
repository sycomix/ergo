import os
import argparse
import logging as log

from ergo.core.optimizer import optimize_dataset
from ergo.dataset import Dataset

def probability(x):
    x = float(x)
    if x < 0 or x > 1:
        raise argparse.ArgumentTypeError("%r not in range [0.0 - 1.0]" % x )
    return x

def parse_args(argv):
    parser = argparse.ArgumentParser(prog="ergo optimize-dataset", description="Remove duplicates from the dataset and only allow them within a given reuse ratio.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("path", help="Path of the project to create.")

    parser.add_argument("-r", "--reuse-ratio", dest="reuse", action="store", type=probability, default=0.15,
        help="Reuse ratio of duplicates in the [0,1] range.")
    parser.add_argument("-o", "--output", dest="output", action="store", default=None,
        help="Output dataset file.")

    return parser.parse_args(argv)

def action_optimize_dataset(argc, argv):
    args = parse_args(argv)
    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        log.error("dataset file %s does not exist", path)
        quit()
    
    optimize_dataset(path, args.reuse, args.output)
