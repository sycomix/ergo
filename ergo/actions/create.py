import sys
import os
import argparse
import logging as log

from ergo.project import Project
from ergo.templates import Templates

def parse_args(argv):
    parser = argparse.ArgumentParser(prog="ergo create", description="Create a new ergo project.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("path", help="Path of the project to create.")

    parser.add_argument("-i", "--inputs", dest="num_inputs", action="store", type=int, default=10,
        help="Number of inputs of the model.")
    parser.add_argument("-o", "--outputs", dest="num_outputs", action="store", type=int, default=2,
        help="Number of outputs of the model.")
    parser.add_argument("-l", "--layers", dest="hidden", action="store", type=str, default="30, 30",
        help="Comma separated list of positive integers, one per each hidden layer representing its size.")
    parser.add_argument("-b", "--batch-size", dest="batch_size", action="store", type=int, default=64,
        help="Batch size parameter for training.")
    parser.add_argument("-e", "--epochs", dest="max_epochs", action="store", type=int, default=50,
        help="Maximum number of epochs to train the model.")

    return parser.parse_args(argv)

def action_create(argc, argv):
    args = parse_args(argv)
    if os.path.exists(args.path):
        log.error(f"path {args.path} already exists")
        quit()

    check = [n for n in [int(s.strip()) for s in args.hidden.split(',') if s.strip() != ""] if n > 0]
    if not check:
        log.error("the --hidden argument must be a comma separated list of at least one positive integer")
        quit()

    ctx = {
        'NUM_INPUTS': args.num_inputs,
        'HIDDEN':     ', '.join([str(n) for n in check]),
        'NUM_OUTPUTS': args.num_outputs,
        'BATCH_SIZE': args.batch_size,
        'MAX_EPOCHS': args.max_epochs,
    }

    log.info("initializing project %s with ANN %d(%s)%d ...", args.path, ctx['NUM_INPUTS'], ctx['HIDDEN'], ctx['NUM_OUTPUTS'])
    os.makedirs(args.path, exist_ok=True)
    for tpl in Templates:
        log.info( "creating %s", tpl.name)
        with open( os.path.join(args.path, tpl.name), 'wt' ) as fp:
            data = tpl.compile(ctx)  
            fp.write(data)
