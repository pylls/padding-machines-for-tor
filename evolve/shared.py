#!/usr/bin/env python3
import numpy as np
import os
import sys
from torch.utils import data
import torch.nn as nn

def metrics(threshold, predictions, labels, label_unmon):
    ''' Computes a range of metrics.

    For details on the metrics, see, e.g., https://www.cs.kau.se/pulls/hot/baserate/
    '''
    tp, fpp, fnp, tn, fn, accuracy, recall, precision, f1 = 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0

    # extended metric: per-class monitored stats
    monitored_right = {}
    monitored_total = {}

    for i in range(len(predictions)):
        label_pred = np.argmax(predictions[i])
        prob_pred = max(predictions[i])
        label_correct = labels[i]

        # we split on monitored or unmonitored correct label
        if label_correct != label_unmon:
            monitored_total[label_correct] = monitored_total.get(label_correct, 0) + 1
            # either confident and correct,
            if prob_pred >= threshold and label_pred == label_correct:
                tp = tp + 1
                monitored_right[label_pred] = monitored_right.get(label_pred, 0) + 1
            # confident and wrong monitored label, or
            elif prob_pred >= threshold and label_pred != label_unmon:
                fpp = fpp + 1
            # wrong because not confident or predicted unmonitored for monitored
            else:
                fn = fn + 1
        else:
            if prob_pred < threshold or label_pred == label_unmon: # correct prediction?
                tn = tn + 1
            elif label_pred < label_unmon: # predicted monitored for unmonitored
                fnp = fnp + 1
            else: # this should never happen
                sys.exit(f"this should never, wrongly labelled data for {label_pred}")

    if tp + fn + fpp > 0:
        recall = round(float(tp) / float(tp + fpp + fn), 4)
    if tp + fpp + fnp > 0:
        precision = round(float(tp) / float(tp + fpp + fnp), 4)

    if precision > 0 and recall > 0:
        f1 = round(2*((precision*recall)/(precision+recall)), 4)

    accuracy = round(float(tp + tn) / float(tp + fpp + fnp + fn + tn), 4)

    return tp, fpp, fnp, tn, fn, accuracy, recall, precision, f1, monitored_right, monitored_total


class Dataset(data.Dataset):
   def __init__(self, ids, dataset, labels):
       self.ids = ids
       self.dataset = dataset
       self.labels = labels

   def __len__(self):
       return len(self.ids)

   def __getitem__(self, index):
       ID = self.ids[index]
       return self.dataset[ID], self.labels[ID]

def load_dataset(
    mon_dir, unm_dir, 
    classes, partitions, samples,
    length, extract_func
    ):
    ''' Loads the dataset from disk into two dictionaries for data and labels.

    The dictionaries are indexed by sample ID. The ID encodes if its a monitored
    or unmonitored sample to make it easier to debug, as well as some info about
    the corresponding data file on disk. 

    This function works assumes the structure of the following dataset:
    - "top50-partitioned-reddit-levels-cirucitpadding" 
    '''
    data = {}
    labels = {}

    # load monitored data
    for c in range(0,classes):
        for p in range(0,partitions):
            site = c*10 + p
            for s in range(0,samples):
                ID = f"m-{c}-{p}-{s}"
                labels[ID] = c

                # file format is {site}-{sample}.trace
                fname = f"{site}-{s}.trace"
                with open(os.path.join(mon_dir, fname), "r") as f:
                    data[ID] = extract_func(f.read(), length)

    # load unmonitored data
    dirlist = os.listdir(unm_dir)
    # make sure we only load a balanced dataset
    dirlist = dirlist[:len(data)]
    for fname in dirlist:
        ID = f"u-{fname}"
        labels[ID] = classes # start from 0 for monitored
        with open(os.path.join(unm_dir, fname), "r") as f:
            data[ID] = extract_func(f.read(), length)

    return data, labels

CIRCPAD_EVENT_NONPADDING_SENT = "circpad_cell_event_nonpadding_sent"
CIRCPAD_EVENT_NONPADDING_RECV = "circpad_cell_event_nonpadding_received"
CIRCPAD_EVENT_PADDING_SENT = "circpad_cell_event_padding_sent"
CIRCPAD_EVENT_PADDING_RECV = "circpad_cell_event_padding_received"
CIRCPAD_ADDRESS_EVENT = "connection_ap_handshake_send_begin"

def trace2cells(log, length, strip=True):
    ''' A fast specialised function to generate cells from a trace.

    Based on circpad_to_wf() in circpad-sim/common.py, but only for cells.
    '''
    data = np.zeros((1, length), dtype=np.float32)
    n = 0

    if strip:
        for i, line in enumerate(log):
            if CIRCPAD_ADDRESS_EVENT in line:
                log = log[i:]
                break

    s = log.split("\n")
    for line in s:
        # outgoing is positive
        if CIRCPAD_EVENT_NONPADDING_SENT in line or \
           CIRCPAD_EVENT_PADDING_SENT in line:
            data[0][n] = 1.0
            n += 1
        # incoming is negative
        elif CIRCPAD_EVENT_NONPADDING_RECV in line or \
           CIRCPAD_EVENT_PADDING_RECV in line:
            data[0][n] = -1.0
            n += 1
        
        if n == length:
            break

    return data

def split_dataset(
    classes, partitions, samples, fold, labels, multiplier=1,
    ):
    '''Splits the dataset based on fold.

    The split is only based on IDs, not the actual data. The result is a 8:1:1
    split into training, validation, and testing.
    '''
    training = []
    validation = []
    testing = []

    # monitored, split by _partition_
    for c in range(0,classes):
        for p in range(0,partitions):
            for s in range(0,samples):
                for x in range(0,multiplier):
                    ID = f"m-{c}-{p}-{s}"
                    if multiplier > 1:
                        ID = f"{ID}-{x}"

                    i = (p+fold) % partitions
                    if i < partitions-2:
                        training.append(ID)
                    elif i < partitions-1:
                        validation.append(ID)
                    else:
                        testing.append(ID)

    # unmonitored
    counter = 0
    for k in labels.keys():
        if not k.startswith("u"):
            continue
        i = (counter+fold) % partitions
        if i < partitions-2:
            training.append(k)
        elif i < partitions-1:
            validation.append(k)
        else:
            testing.append(k)     
        counter += 1

    split = {}
    split["train"] = training
    split["validation"] = validation
    split["test"] = testing
    return split

def zero_dataset(dataset, z):
    index = z.split(":")
    start = int(index[0])
    stop = int(index[1])
    data = np.zeros((stop-start), dtype=np.float32)
    for k, v in dataset.items():
        v[:,start:stop] = data
        dataset[k] = v
    return dataset

class DFNet(nn.Module):
    def __init__(self, classes, fc_in_features = 512*10):
        super(DFNet, self).__init__()
        # https://ezyang.github.io/convolution-visualizer/index.html
        # https://github.com/lin-zju/deep-fp/blob/master/lib/modeling/backbone/dfnet.py
        self.kernel_size = 7
        self.padding_size = 3
        self.pool_stride_size = 4
        self.pool_size = 7

        self.block1 = self.__block(1, 32, nn.ELU())
        self.block2 = self.__block(32, 64, nn.ReLU())
        self.block3 = self.__block(64, 128, nn.ReLU())
        self.block4 = self.__block(128, 256, nn.ReLU())

        self.fc = nn.Sequential(
            nn.Linear(fc_in_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.7),
            nn.Linear(512, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.5)
        )

        self.prediction = nn.Sequential(
            nn.Linear(512, classes),
            # when using CrossEntropyLoss, already computed internally
            #nn.Softmax(dim=1) # dim = 1, don't softmax batch
        )
    
    def __block(self, channels_in, channels, activation):
        return nn.Sequential(
            nn.Conv1d(channels_in, channels, self.kernel_size, padding=self.padding_size),
            nn.BatchNorm1d(channels),
            activation,
            nn.Conv1d(channels, channels, self.kernel_size, padding=self.padding_size),
            nn.BatchNorm1d(channels),
            activation,
            nn.MaxPool1d(self.pool_size, stride=self.pool_stride_size, padding=self.padding_size),
            nn.Dropout(p=0.1)
        )

    def forward(self, x):
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = x.flatten(start_dim=1) # dim = 1, don't flatten batch
        x = self.fc(x)
        x = self.prediction(x)

        return x