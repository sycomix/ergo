import argparse
import json
import logging as log
import time
import numpy as np

from terminaltables import AsciiTable

from ergo.core.queue import TaskQueue
from ergo.project import Project

# https://stackoverflow.com/questions/11942364/typeerror-integer-is-not-json-serializable-when-serializing-json-in-python
def default(o):
    if isinstance(o, np.int64): return int(o)
    raise TypeError

def validate_args(args):
    if args.ratio > 1.0 or args.ratio <= 0:
        log.error("ratio must be in the (0.0, 1.0] interval")
        quit()

def parse_args(argv):
    parser = argparse.ArgumentParser(prog="ergo relevance", description="Compute the relevance of each feature of the dataset by differential evaluation.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("path", help="Path of the project.")

    parser.add_argument("-d", "--dataset", dest="dataset", action="store", type=str, required=True,
        help="Dataset file to use.")
    parser.add_argument("-m", "--metric", dest="metric", action="store", type=str, default='precision',
        help="Which metric to track changes of while performing differential evaluation.")
    parser.add_argument("-a", "--attributes", dest="attributes", action="store", type=str, required=False,
        help="Optional file containing the attribute names, one per line.")
    parser.add_argument("-r", "--ratio", dest="ratio", action="store", type=float, required=False, default=1.0,
        help="Size of the subset of the dataset to use in the (0,1] interval.")
    parser.add_argument("-j", "--to-json", dest="to_json", action="store", type=str, required=False,
        help="Output the relevances to this json file.")
    parser.add_argument("-w", "--workers", dest="workers", action="store", type=int, default=0,
        help="If 0, the algorithm will run a single thread iteratively, otherwise create a number of workers " + \
             "to distribute the computation among, -1 to use the number of logical CPU cores available. WARNING: " + \
             "The dataset will be copied in memory for each worker."   )

    return parser.parse_args(argv)

def get_attributes(filename, ncols):
    attributes = []
    if filename is not None:
        with open(filename) as f:
            attributes = f.readlines()
        attributes = [name.strip() for name in attributes]
    else:
        attributes = ["feature %d" % i for i in range(0, ncols)]

    return attributes

def zeroize_feature(X, col, is_scalar_input):
    if is_scalar_input:
        backup = X[:, col].copy()
        X[:,col] = 0
    else:
        backup = X[col].copy()
        X[col] = np.zeros_like(backup)

    return backup

def restore_feature(X, col, backup, is_scalar_input):
    if is_scalar_input:
        X[:,col] = backup
    else:
        X[col] = backup


prj    = None
deltas = []
tot    = 0
ncols  = 0
nrows  = 0
start  = None
speed  = 0
attributes = None

def run_inference_without(X, y, col, flat, ref, metric):
    global prj, deltas, tot, start, speed, nrows, ncols, attributes

    log.info("[%.2f evals/s] computing relevance for attribute [%d/%d] %s ...", speed, col + 1, ncols, attributes[col])

    copy = X.copy()
    zeroize_feature(copy, col, flat)

    start = time.time()

    accu, cm = prj.accuracy_for(copy, y, repo_as_dict = True)

    speed = (1.0 / (time.time() - start)) * nrows

    delta = ref - accu['weighted avg'][metric]
    tot  += delta

    deltas.append((col, delta))

def action_relevance(argc, argv):
    global prj, deltas, tot, start, speed, nrows, ncols, attributes

    args = parse_args(argv)
    prj = Project(args.path)
    err = prj.load()
    if err is not None:
        log.error("error while loading project: %s", err)
        quit()
    elif not prj.is_trained():
        log.error("no trained Keras model found for this project")
        quit()

    prj.prepare(args.dataset, 0.0, 0.0)

    # one single worker in blocking mode = serial
    if args.workers == 0:
        args.workers = 1

    X, y         = prj.dataset.subsample(args.ratio)
    nrows, ncols = X.shape if prj.dataset.is_flat else (X[0].shape[0], len(X))
    attributes   = get_attributes(args.attributes, ncols)
    queue        = TaskQueue('relevance', num_workers=args.workers, blocking=True)
   
    if args.workers == 1:
        log.info("computing relevance of %d attributes on %d samples using '%s' metric (slow mode) ...", ncols, nrows, args.metric)
    else:
        log.info("computing relevance of %d attributes on %d samples using '%s' metric (parallel with %d workers) ...", ncols, nrows, args.metric, queue.num_workers)

    start = time.time()
    ref_accu, ref_cm = prj.accuracy_for(X, y, repo_as_dict = True)
    speed = (1.0 / (time.time() - start)) * nrows

    for col in range(0, ncols):
        queue.add_task( run_inference_without, 
                X, y, col, prj.dataset.is_flat, 
                ref_accu['weighted avg'][args.metric], 
                args.metric) 

    # wait for all inferences to finish
    queue.join()
    # sort relevances by absolute value
    deltas = sorted(deltas, key = lambda x: abs(x[1]), reverse = True)

    rels     = []
    num_zero = 0
    table    = [("Column", "Feature", "Relevance")]

    for delta in deltas:
        col, d = delta
        colname = attributes[col]
        rel = {
            "attribute": colname,
            "index": col, 
            "relevance": 0.0     
        }

        if d != 0.0:
            relevance = (d / tot) * 100.0
            row       = ("%d" % col, attributes[col], "%.2f%%" % relevance)
            row       = ["\033[31m%s\033[0m" % e for e in row] if relevance < 0.0 else row
            table.append(row)
            rel['relevance'] = relevance
        else:
            num_zero += 1

        rels.append(rel)

    print("")
    print(AsciiTable(table).table)
    print("")

    if num_zero > 0:
        log.info("%d features have 0 relevance.", num_zero)

    if args.to_json is not None:
        print("")
        log.info("creating %s ...", args.to_json)
        with open(args.to_json, 'w+') as fp:
            json.dump(rels, fp, default=default)
