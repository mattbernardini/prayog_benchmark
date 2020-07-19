# -*- coding: utf-8 -*-
"""Benchmark.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1tPTB7y1gj6v78djK5E95LCcGQdv1rht1

# Prep for Benchmark
"""

# Commented out IPython magic to ensure Python compatibility.
from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf
import numpy as np
import math
import matplotlib.pyplot as plt
import string
import pickle
import glob
import os
import sys
import itertools
import datetime

import inspect
from typing import List

import scipy


from tcn import TCN, tcn_full_summary

for gpu in tf.config.experimental.list_physical_devices('GPU'):
	print('Setting gpu growth for', gpu)
	tf.config.experimental.set_memory_growth(gpu, True)

# Constants we declare for the scope of the file
LENGTH_OF_INPUTS    = 512
BATCH_SIZE          = 64
NUM_EPOCHS          = 2
NUM_EXAMPLES        = 150
NUM_TEST_EXAMPLES   = 10
NUM_INPUT_CHANNELS  = 42
NUM_OUTPUT_CHANNELS = 100
MIN_L               = 12

# Adapted from trRosetta, but works for fasta as well
# read A3M and convert letters into integers in the 0..20 range
def parse_a3m(seq_line):
    seqs = []
    table = str.maketrans(dict.fromkeys(string.ascii_lowercase))
    seqs.append(seq_line.rstrip().translate(table))
    # convert letters into numbers
    alphabet = np.array(list("ARNDCQEGHILKMFPSTWYV"), dtype='|S1').view(np.uint8)
    msa = np.array([list(s) for s in seqs], dtype='|S1').view(np.uint8)
    for i in range(alphabet.shape[0]):
        msa[msa == alphabet[i]] = i
    assert msa.max() < 20 # for sequences without gaps
    return msa

def one_hot(a, num_classes):
  return np.squeeze(np.eye(num_classes)[a.reshape(-1)])

def get_feature(pdb, expected_n_channels = 20 + 22):
    features = pickle.load(open(pdb, 'rb'))
    l = len(features['seq'])
    seq = features['seq']
    seq1hot = one_hot(parse_a3m(seq), 20)
    assert seq1hot.shape == (l, 20)
    # Create X and Y placeholders
    X = np.zeros((l, expected_n_channels))
    # Add PSSM
    pssm = features['pssm']
    assert pssm.shape == (l, 22)
    pssm[:, -1] /= np.max(pssm[:, -1])
    X[:, :20] = seq1hot
    X[:, 20:] = pssm
    assert X.max() < 100.0
    assert X.min() > -100.0
    return X

def get_map(pdb, expected_l = -1):
    (ly, seqy, cb_map) = np.load(pdb, allow_pickle = True)
    Y = cb_map
    Y [Y < 3.0] = 3.0
    Y [Y > 30.0] = 30.0
    return Y.astype(np.float32)

def map_to_dist_profile(dmap):
    l = len(dmap[:, 0])
    max_seq_sep = 100
    #dist_profile = np.full((l, max_seq_sep), np.nan)
    dist_profile = np.full((l, max_seq_sep), 100.0)
    for rnum in range(l):
        for ss in range(1, max_seq_sep):
            if rnum - ss < 1:
                continue
            dist_profile[rnum, ss] = dmap[rnum, rnum - ss]
    return dist_profile

from math import sqrt
import numpy as np
import math

################################################################################
valid_amino_acids = {
    'LLP': 'K', 'TPO': 'T', 'CSS': 'C', 'OCS': 'C', 'CSO': 'C', 'PCA': 'E', 'KCX': 'K', \
    'CME': 'C', 'MLY': 'K', 'SEP': 'S', 'CSX': 'C', 'CSD': 'C', 'MSE': 'M', \
    'ALA': 'A', 'ASN': 'N', 'CYS': 'C', 'GLN': 'Q', 'HIS': 'H', 'LEU': 'L', \
    'MET': 'M', 'MHO': 'M', 'PRO': 'P', 'THR': 'T', 'TYR': 'Y', 'ARG': 'R', 'ASP': 'D', \
    'GLU': 'E', 'GLY': 'G', 'ILE': 'I', 'LYS': 'K', 'PHE': 'F', 'SER': 'S', \
    'TRP': 'W', 'VAL': 'V', 'SEC': 'U'
    }

################################################################################
def check_pdb_valid_row(valid_amino_acids, l):
    if (get_pdb_rname(l) in valid_amino_acids.keys()) and (l.startswith('ATOM') or l.startswith('HETA')):
        return True
    return False

################################################################################
def get_pdb_atom_name(l):
    return l[12: 16].strip()

################################################################################
def get_pdb_rnum(l):
    return int(l[22: 27].strip())

################################################################################
def get_pdb_rname(l):
    return l[17: 20].strip()

################################################################################
def get_pdb_xyz_cb(lines):
    xyz = {}
    for l in lines:
        if get_pdb_atom_name(l) == 'CB':
            xyz[get_pdb_rnum(l)] = (float(l[30:38].strip()), float(l[38:46].strip()), float(l[46:54].strip()))
    for l in lines:
        if (get_pdb_rnum(l) not in xyz) and get_pdb_atom_name(l) == 'CA':
            xyz[get_pdb_rnum(l)] = (float(l[30:38].strip()), float(l[38:46].strip()), float(l[46:54].strip()))
    return xyz

################################################################################
def get_pdb_xyz_ca(lines):
    xyz = {}
    for l in lines:
        if get_pdb_atom_name(l) == 'CA':
            xyz[get_pdb_rnum(l)] = (float(l[30:38].strip()), float(l[38:46].strip()), float(l[46:54].strip()))
    return xyz

################################################################################
def get_dist_maps(valid_amino_acids, file_pdb):
    f = open(file_pdb, mode = 'r')
    flines = f.read()
    f.close()
    lines = flines.splitlines()
    templines = flines.splitlines()
    for l in templines:
        if not l.startswith('ATOM'):
            lines.remove(l)

    # We have filtered out all non ATOMs at this point
    rnum_rnames = {}
    for l in lines:
        atom = get_pdb_atom_name(l)
        if atom != 'CA':
            continue
        #if int(get_pdb_rnum(l)) in rnum_rnames:
            #warnings.warn ('Warning!! ' + file_pdb + ' - multiple CA rows - rnum = ' + str(get_pdb_rnum(l)))
        if not get_pdb_rname(l) in valid_amino_acids.keys():
            print ('' + get_pdb_rname(l) + ' is unknown amino acid in ' + l)
            sys.exit(1)
        rnum_rnames[int(get_pdb_rnum(l))] = valid_amino_acids[get_pdb_rname(l)]
    seq = ""
    for i in range(max(rnum_rnames.keys())):
        if i+1 not in rnum_rnames:
            print (rnum_rnames)
            print ('Error! ' + file_pdb + ' ! residue not defined for rnum = ' + str(i+1))
            sys.exit (1)
        seq = seq + rnum_rnames[i+1]
    L = len(seq)
    xyz_cb = get_pdb_xyz_cb(lines)
    if len(xyz_cb) != L:
        print(rnum_rnames)
        for i in range(L):
            if i+1 not in xyz_cb:
                print('XYZ not defined for ' + str(i+1))
        print ('Error! ' + file_pdb + ' Something went wrong - len of cbxyz != seqlen!! ' + str(len(xyz_cb)) + ' ' +  str(L))
        sys.exit(1)
    cb_map = np.zeros((L, L))
    for r1 in sorted(xyz_cb):
        (a, b, c) = xyz_cb[r1]
        for r2 in sorted(xyz_cb):
            (p, q, r) = xyz_cb[r2]
            cb_map[r1 - 1, r2 - 1] = sqrt((a-p)**2+(b-q)**2+(c-r)**2)
    xyz_ca = get_pdb_xyz_ca(lines)
    if len(xyz_ca) != L:
        print ('Something went wrong - len of cbxyz != seqlen!! ' + str(len(xyz_ca)) + ' ' +  str(L))
        sys.exit(1)
    ca_map = np.zeros((L, L))
    for r1 in sorted(xyz_ca):
        (a, b, c) = xyz_ca[r1]
        for r2 in sorted(xyz_ca):
            (p, q, r) = xyz_ca[r2]
            ca_map[r1 - 1, r2 - 1] = sqrt((a-p)**2+(b-q)**2+(c-r)**2)
    return L, seq, cb_map, ca_map

all_sentences = []
all_dist_labels = []
SEQUENCE_LENGTHS = []

# Takes in any protein's input features and output distances
# Returns many overlapping crops of the input features and output distances as two lists
# It probably is a good idea to reduce out_l = 512 but
#  this has to be done carefully by considering the case of L > out_l
def make_sentences_nextchars(x, y, min_l = 12, out_l = 512, stride = 1):
    sentences = []
    dist_labels = []
    L = len(x[:, 0])
    for i in range(min_l, L, stride):
        myx = np.zeros((out_l, len(x[0, :])))
        if i > out_l:
            myx[-i:, :] = x[(i-out_l):i, :]
        else:
            myx[-i:, :] = x[:i, :]
        sentences.append(myx)
        dist_labels.append(y[i])        
    return (sentences, dist_labels)

# A set of 150 proteins (PSICOV set)
for dist_file, i in zip(glob.glob("./data/deepcov/distance/*.npy"), range(NUM_EXAMPLES)):
    id = os.path.splitext(os.path.basename(dist_file))[0][:5]
    dmap = get_map(dist_file)
    # This is the input (X) to the 1D CNN/LSTM architecture
    input_feature = get_feature('./data/deepcov/features/'+ id + '.pkl')
    # This is the output (Y) to the model
    output_dist_profile = map_to_dist_profile(dmap)
    l = len(input_feature[:, 0])
    Y = 100.0 / output_dist_profile
    this_sentences, dist_labels = make_sentences_nextchars(input_feature, Y, out_l=LENGTH_OF_INPUTS, min_l=MIN_L)
    SEQUENCE_LENGTHS.append(len(this_sentences) + 1)
    all_sentences.extend(this_sentences)
    all_dist_labels.extend(dist_labels)

print('Vectorization...')
x = np.zeros((len(all_sentences), LENGTH_OF_INPUTS, NUM_INPUT_CHANNELS))
y = np.zeros((len(all_sentences), NUM_OUTPUT_CHANNELS))
for i, sentence in enumerate(all_sentences):
    x[i] = all_sentences[i]
    y[i] = all_dist_labels[i]

num_examples_in_training_set = sum(SEQUENCE_LENGTHS[:NUM_TEST_EXAMPLES])

X = np.zeros((NUM_EXAMPLES, LENGTH_OF_INPUTS, NUM_INPUT_CHANNELS))
Y = np.zeros((NUM_EXAMPLES, LENGTH_OF_INPUTS, NUM_OUTPUT_CHANNELS))

# A set of 150 proteins (PSICOV set)
i = 0
for dist_file in glob.glob("./data/psicov/distance/*.npy"):
    id = os.path.splitext(os.path.basename(dist_file))[0][:5]
    dmap = get_map(dist_file)
    # This is the input (X) to the 1D CNN/LSTM architecture
    input_feature = get_feature('./data/psicov/features/'+ id + '.pkl')
    # This is the output (Y) to the model
    output_dist_profile = map_to_dist_profile(dmap)
    l = len(input_feature[:, 0])
    X[i, -l:, :] = input_feature
    Y[i, -l:, :] = 100.0 / output_dist_profile
    i += 1

""" # ResNet CNN """

my_input = tf.keras.layers.Input(shape = (512, 42))
tower = tf.keras.layers.Conv1D(512, 21, padding = 'same')(my_input)
tower = tf.keras.layers.Activation('relu')(tower)
tower = tf.keras.layers.BatchNormalization()(tower)
for i in range(8):
    block = tf.keras.layers.Conv1D(512, 11, padding = 'same')(tower)
    block = tf.keras.layers.Activation('relu')(block)
    block = tf.keras.layers.BatchNormalization()(block)
    block = tf.keras.layers.Conv1D(512, 11, padding = 'same')(block)
    block = tf.keras.layers.Activation('relu')(block)
    block = tf.keras.layers.BatchNormalization()(block)
    tower = tf.keras.layers.add([block, tower])
tower = tf.keras.layers.Conv1D(100, 11, padding = 'same')(tower)
tower = tf.keras.layers.Activation('relu')(tower)
res_net_model = tf.keras.models.Model(my_input, tower)
res_net_model.compile(loss='logcosh', optimizer='adam', metrics=['mae'])
print(res_net_model.summary())

time_elapsed = datetime.datetime.now()
res_net_model.fit(X[:140], 
                    Y[:140], 
                    validation_data=(X[140:], Y[140:]), 
                    epochs=NUM_EPOCHS, 
                    batch_size=BATCH_SIZE, 
                    callbacks=[])
print(f"\nTIME ELAPSED: {datetime.datetime.now() - time_elapsed}\n")
