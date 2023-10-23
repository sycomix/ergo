import os
import shutil
import logging as log
import numpy as np

from collections import defaultdict

def clean_if_exist(path, files):
    path  = os.path.abspath(path)
    for filename in files:
        filename = os.path.join(path, filename)
        if os.path.exists(filename):
            if os.path.isdir(filename):
                log.info("removing folder %s", filename)
                shutil.rmtree(filename)
            else:
                log.info("removing file %s", filename)
                os.remove(filename)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def serialize_classification_report(cr):
    tmp = []
    for row in cr.split("\n"):
        if parsed_row := [
            x.strip() for x in row.split("  ") if len(x.strip()) > 0
        ]:
            tmp.append(parsed_row)

    measures = tmp[0]
    out = defaultdict(dict)
    for row in tmp[1:]:
        columns      = len(row)
        class_label  = row[0].strip()
        num_measures = len(measures)

        # fixes https://github.com/evilsocket/ergo/issues/5
        while columns < num_measures + 1:
            row.insert(1, None)
            columns += 1

        for j, m in enumerate(measures):
            v = row[j + 1]
            value = float(v.strip()) if v is not None else None
            metric = m.strip()
            out[class_label][metric] = value

    return out

def serialize_cm(cm):
    return cm.tolist()
