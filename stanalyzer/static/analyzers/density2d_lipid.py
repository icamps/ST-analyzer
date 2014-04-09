#/usr/bin/env python

#----------------------------------------------------------------------------------------
# Author: Jong Cheol Jeong (korjcjeong@yahoo.com, people.eecs.ku.edu/~jjeong)
# 	  Bioinformatics center, The University of Kansas
#----------------------------------------------------------------------------------------

# for MDAnalysis
import sys
from MDAnalysis import *
from MDAnalysis.analysis.align import *
import math
import numpy as np

# for server side jobs
import os
import string
import random
import subprocess

# import others
import pprint
import pickle
import re
from datetime import datetime
from collections import defaultdict	# for initializing dictionary


# for using sqlite3
import sqlite3
import stanalyzer
import lipidArea

# for local functions and classes
from stanalyzer import *

#**********************************************************************
# *  This function analyzer the system box through all trajectories
#
#**********************************************************************

#///////////////////////////////////////////////////////////////////////////
# Get job information
# -- Use following codes to make your own function
#///////////////////////////////////////////////////////////////////////////
exe_file = sys.argv[0];
in_file = sys.argv[1];
ST_para_idx = int(sys.argv[2]);         # parameter index for multiple jobs in a same form
fid_in = open(in_file, 'rb');
dic = pickle.load(fid_in);
fid_in.close();

# variables in binary file
ST_para_pkeys      = dic["para_pkeys"];        # gui_parameter primary keys obtained from job submitting
ST_job_pkey        = dic["job_pkey"];          # gui_job primary keys obtained from job submitting
ST_job_title       = dic["job_title"];         # gui_job title
ST_prj_pkey        = dic["pkey"];              # gui_project primary key beloning to current job
ST_prj_title       = dic["ptitle"];            # gui_project title beloning to current job
ST_SESSION_HOME    = dic["session_home"];      # default session home directory: ~/dJango_home/media/user_id
ST_OUTPUT_HOME     = dic["output_home"];       # output directory given by user
ST_PBS_HOME        = dic["pbs_home"];          # directory where PBS script is written (i.e. for using cluster)
ST_ANALYZER_HOME   = dic["analyzer_home"];     # directory where all analyzers are located (i.e. the location of this file)
ST_MEDIA_HOME      = dic["media_home"];        # media directory ~/dJango_home/media
ST_DB_FILE         = dic["dbName"];            # database file name and full location 
ST_base_path       = dic["base_path"];         # base location of input files
ST_path_output     = dic["path_output"];       # the location of output directory
ST_path_python     = dic["path_python"];       # python path to run analyzers
ST_structure_file  = dic["structure_file"];    # full path of structure file (i.e. PDB, PSF, etc)
pdb_file  	   = dic["pdb_file"];          # full path of structure file (i.e. PDB)
ST_pbs             = dic["pbs"];               # PBS script for using cluster machine
ST_num_frame	   = dic["num_frame"];         # number of frames in the first trajectory file
ST_num_atoms	   = dic["num_atoms"];         # number of atomes in the system
ST_num_files	   = dic["num_files"];         # number of files chosen
ST_num_ps	   = str(dic["num_ps"]);       # simulation time ps/frame
ST_trajectoryFile = [];                        # the list of trajectory files
ST_STATIC = ST_ANALYZER_HOME[0:len(ST_ANALYZER_HOME)-10];  # directory where ~/dJango_home/static

for i in range(len(dic["trajectory"])):
    ST_trajectoryFile.append(dic["trajectory"][i]);

# Identifying my parameters
myPara = get_myfunction(exe_file, dic);
fName = myPara[0];      # name of function except '.py'
pInfo = myPara[1];      # parameter information pInfo[0] = "number of parameters"
paras = myPara[2];      # actual parameters paras[0] contains 'the number of parameters'
para_pkey = myPara[3];  # primary key of parameter table contating this analzyer function. 
ST_rmodule   = "{0}{1}".format(exe_file[:len(exe_file)-3], ST_para_idx);  # running module name (e.g. box0)

#---------------------< assigned module specific parameters: fixed for every interface >---------------------------------
ST_num_paras = paras[0][0];		# pInfo[0] : number of parameters
ST_frmInt    = paras[1][ST_para_idx];	# pInfo[1] : Frame interval (list)
ST_frmInt    = int(ST_frmInt);
ST_outFile   = paras[2][ST_para_idx];	# pInfo[2] : output file name (list)

# Updating DB: running Job
# 0 - submit job
# 1 - Running job
# 2 - Error occurred
# 3 - Completed
stime = datetime.now().strftime("%Y-%m-%d %H:%M:%S");
conn = sqlite3.connect(ST_DB_FILE);
c    = conn.cursor();
for i in range(len(para_pkey)):
    query = """UPDATE gui_parameter SET status = "RUNNING" WHERE id = {}""".format(para_pkey[i]);
    c.execute(query);
    conn.commit();
conn.close();

# Update values into gui_outputs
conn = sqlite3.connect(ST_DB_FILE);
c    = conn.cursor();
# find gui_outputs related to current processing
jobName = "{}_{}".format(ST_rmodule, ST_outFile);
query = """SELECT id FROM gui_outputs WHERE job_id = {0} and name = "{1}" """.format(ST_job_pkey[0], jobName);
c.execute(query);
row = c.fetchone();
pk_output = row[0];     # primary key for gui_outputs
try:    
    query = """UPDATE gui_outputs SET status = "Running" WHERE id = {0}""".format(pk_output);
    c.execute(query);
    conn.commit();
    conn.close();
except:
    conn = sqlite3.connect(ST_DB_FILE);
    c    = conn.cursor();
    query = """UPDATE gui_outputs SET status = "Failed" WHERE id = {0}""".format(pk_output);
    c.execute(query);
    conn.commit();
    conn.close();


ST_out_dir = "{}{}".format(ST_OUTPUT_HOME, fName[1]);
# Create output directory
if not (os.path.isdir(ST_out_dir)):
    os.mkdir(ST_out_dir);


# -------- Writing input file for web-link
inFile = '{0}/input{1}.dat'.format(ST_out_dir, ST_para_idx);
fid_in = open(inFile, 'w');
strPara = "Name of Function: {}\n".format(exe_file);
strPara = strPara + "System information \n";
strPara = strPara + "\t- First trajectory contains {0} frames ({1} ps/frame)\n".format(ST_num_frame, ST_num_ps);
strPara = strPara + "\t- There are {0} trajectory file(s) and {1} atoms\n".format(ST_num_files, ST_num_atoms);
strPara = strPara + "Total {} parameters \n".format(int(paras[0][0])+3);
strPara = strPara + "\t- Base path: {}\n".format(ST_base_path);
strPara = strPara + "\t- Structure file: {}\n".format(ST_structure_file);
strPara = strPara + "\t- Trajectory files: \n"
tmp = "";
for trj in ST_trajectoryFile:
    tmp = tmp + "\t\t{}\n".format(trj);
    
strPara = strPara + tmp;

strPara = strPara + "\t- Job specific parameters: \n"
strPara = strPara + "\t\t{0}:{1}\n".format(pInfo[0], paras[0][0]);
tmp = "";
for i in range(len(pInfo)):
    if i > 0:
	tmp = tmp + "\t\t{0}:{1}\n".format(pInfo[i], paras[i][ST_para_idx]);
strPara = strPara + tmp;
strPara = strPara + "\nPBS: \n{}\n".format(ST_pbs);
fid_in.write(strPara);
fid_in.close();

"""
print '### Parameters in RDF1D.py ###'
print ST_para_idx 	 # parameter index for multiple jobs in a same form
print ST_para_pkeys   	 # gui_parameter primary keys obtained from job submitting
print ST_job_pkey        # gui_job primary keys obtained from job submitting
print ST_job_title       # gui_job title
print ST_prj_pkey        # gui_project primary key beloning to current job
print ST_prj_title       # gui_project title beloning to current job
print ST_SESSION_HOME    # default session home directory: ~/dJango_home/media/user_id
print ST_OUTPUT_HOME     # output directory given by user
print ST_PBS_HOME        # directory where PBS script is written (i.e. for using cluster)
print ST_ANALYZER_HOME   # directory where all analyzers are located (i.e. the location of this file)
print ST_MEDIA_HOME      # media directory ~/dJango_home/media
print ST_DB_FILE         # database file name and full location 
print ST_base_path       # base location of input files
print ST_path_output     # the location of output directory
print ST_path_python     # python path to run analyzers
print ST_structure_file  # full path of structure file (i.e. PDB, PSF, etc)
print ST_pbs             # PBS script for using cluster machine
print ST_num_frame	 # number of frames in the first trajectory file
print ST_num_atoms	 # number of atomes in the system
print ST_num_files	 # number of files chosen
print ST_num_ps	  	 # simulation time ps/frame
print ST_trajectoryFile  # the list of trajectory files
print ST_rmodule   	 # running module name (e.g. box0)
print ST_num_paras 	 # number of parameters
print ST_frmInt	  	 # Frame interval 
print ST_outFile   	 # output file name
"""

#---------------------< assigned global parameters >---------------------------------
# ST_para_idx 	  	# parameter index for multiple jobs in a same form
# ST_para_pkeys   	# gui_parameter primary keys obtained from job submitting
# ST_job_pkey        	# gui_job primary keys obtained from job submitting
# ST_job_title       	# gui_job title
# ST_prj_pkey        	# gui_project primary key beloning to current job
# ST_prj_title       	# gui_project title beloning to current job
# ST_SESSION_HOME    	# default session home directory: ~/dJango_home/media/user_id
# ST_OUTPUT_HOME     	# output directory given by user
# ST_PBS_HOME        	# directory where PBS script is written (i.e. for using cluster)
# ST_ANALYZER_HOME   	# directory where all analyzers are located (i.e. the location of this file)
# ST_STATIC		# static directory ~/dJango_home/static
# ST_MEDIA_HOME      	# media directory ~/dJango_home/media
# ST_DB_FILE         	# database file name and full location 
# ST_base_path       	# base location of input files
# ST_path_output     	# the location of output directory
# ST_path_python     	# python path to run analyzers
# ST_structure_file  	# full path of structure file (i.e. PDB, PSF, etc)
# ST_pbs             	# PBS script for using cluster machine
# ST_num_frame	  	# number of frames in the first trajectory file
# ST_num_atoms	  	# number of atomes in the system
# ST_num_files	  	# number of files chosen
# ST_num_ps	  	# simulation time ps/frame
# ST_trajectoryFile  	# the list of trajectory files
# ST_rmodule   	  	# running module name (e.g. box0)
# ST_num_paras 	  	# number of parameters
# ST_frmInt	  	# Frame interval 
# ST_outFile   	  	# output file name
# ST_out_dir		# output directory

###############################################################################################################################
######################################## PLEASE DO NOT MODIFY ABOVE THIST LINE!!!! ############################################
###############################################################################################################################

#---------------------< assigned module specific parameters: defined by users >---------------------------------
cntQry	= paras[4][ST_para_idx];		# bin size
cntAxs	= paras[5][ST_para_idx];		# bin size
binsize = paras[6][ST_para_idx];		# bin size
binsize = int(binsize);
selQry = paras[7][ST_para_idx];		# selection query 1

sysX    = paras[8][ST_para_idx];		# system size X
sysX 	= round(float(sysX));

sysY    = paras[9][ST_para_idx];		# system size Y
sysY 	= round(float(sysY));

sysZ    = paras[10][ST_para_idx];		# system size Z
sysZ 	= round(float(sysZ));


# defining top and bottom leaflet 
if cntAxs == 'x':
    top_cut = sysX * 0.165;
    btm_cut = -1.0 * top_cut;
    top_selQry = "{} and (prop x > {})".format(selQry, top_cut);
    btm_selQry = "{} and (prop x < {})".format(selQry, btm_cut);
elif cntAxs == 'y':
    top_cut = sysY * 0.165;
    btm_cut = -1.0 * top_cut;
    top_selQry = "{} and (prop y > {})".format(selQry, top_cut);
    btm_selQry = "{} and (prop y < {})".format(selQry, btm_cut);
else:
    top_cut = sysZ * 0.165;
    btm_cut = -1.0 * top_cut;
    top_selQry = "{} and (prop z > {})".format(selQry, top_cut);
    btm_selQry = "{} and (prop z < {})".format(selQry, btm_cut);

# augumented X axis
BIN_X = [];
min_x = math.floor(0.5 * -sysX) - 5.0;
max_x = math.ceil(0.5 * sysX) + 5.0;
for i in stanalyzer.frange(min_x, max_x, binsize):
    BIN_X.append(i);

BIN_Y = [];
min_y = math.floor(0.5 * -sysY) - 5.0;
max_y = math.ceil(0.5 * sysY) + 5.0;
for i in stanalyzer.frange(min_y, max_y, binsize):
    BIN_Y.append(i);

BIN_top = [];
BIN_btm = [];
for i in BIN_X:
    for j in BIN_Y:
	tmp = [i,j, 0.0];
	BIN_top.append(tmp);
	BIN_btm.append(tmp);


print "Okay running...."

#///////////////////////////////////////////////////////////////////////////
# Running actual job
#///////////////////////////////////////////////////////////////////////////
try:
    run = 1;
    if run:
	psf = '{0}{1}'.format(ST_base_path, ST_structure_file);

	for idx in range(len(ST_trajectoryFile)):
	    # turning on periodic boundary conditions
	    MDAnalysis.core.flags['use_periodic_selections'] = True
	    MDAnalysis.core.flags['use_KDTree_routines'] = False
	    
	    # reading trajectory
	    trj = '{0}{1}'.format(ST_base_path, ST_trajectoryFile[idx]);
	    u = Universe(psf, trj);
	    
	    cnt = 0;
	    num_frm = 0.0;
	    
	    # initializing array
	    tmp_topDNST = [[0.0, 0.0, 0.0] for i in range(len(BIN_top))];
	    tmp_btmDNST = [[0.0, 0.0, 0.0] for i in range(len(BIN_btm))];
	    
	    for ts in u.trajectory:
		# flag for top and bottom leaflet
		top_flag = 0; btm_flag = 0;
		
		cnt = cnt + 1;
		
		if (cnt % ST_frmInt) == 0:
		    num_frm = num_frm + 1.0;
		    
		    #######################################################
		    ############## Write your code below ##################
		    #######################################################
		    
		    #======= Centeralization =========
		    if (cntQry != 'no') :
			stanalyzer.centerByRes2(ts, u, cntQry, 1, cntAxs); # 1st residue is always chosen for centering membrane
		    #==================================
    
		    #############################################
		    #### Calculating top and bottom layer #######
		    #############################################
		    ####################
		    #----> top leaflet
		    ####################
		    #print "#top_selQry = {}".format(top_selQry);
		    top_Atoms = u.selectAtoms(top_selQry);
		    top_Res = top_Atoms.resnames();
		    top_IDs = top_Atoms.resids();
		    if len(top_Res) > 0:
			top_flag = top_flag + 1;
			for i in range(len(top_Res)):
			    top_Qry = 'resname {} and resid {} and ({})'.format(top_Res[i], top_IDs[i], selQry);
			    #print "\t-top_Qry: {}".format(top_Qry);
			    Tsel = u.selectAtoms(top_Qry);
			    COM = Tsel.centerOfMass();
			    # finding associated BIN
			    # location of X
			    x = COM[0]; y = COM[1];
			    #print "### TOP leaflet [{}]###".format(num_frm);
			    #print "\tCOM: x={}, y={}".format(x,y);
			    tmp = stanalyzer.count_intervals2(x, BIN_X);
			    loc_x = tmp.index(1);
			    tmp = stanalyzer.count_intervals2(y, BIN_Y);
			    loc_y = tmp.index(1);
			    # count the frequency
			    bin_idx = loc_x * len(BIN_Y) + loc_y;
			    tmp_topDNST[bin_idx][2] = tmp_topDNST[bin_idx][2] + 1.0;
			    #print "\tBIN: x={}, y={}, freq={}".format(BIN_top[bin_idx][0], BIN_top[bin_idx][1], tmp_topDNST[bin_idx][2]);
		    ######################
		    #----> bottom leaflet
		    ######################
		    btm_Atoms = u.selectAtoms(btm_selQry);
		    btm_Res = btm_Atoms.resnames();
		    btm_IDs = btm_Atoms.resids();
		    if len(btm_Res) > 0:
			btm_flag = btm_flag + 1;
			for i in range(len(btm_Res)):
			    btm_Qry = 'resname {} and resid {} and ({})'.format(btm_Res[i], btm_IDs[i], selQry);
			    Tsel = u.selectAtoms(btm_Qry);
			    COM = Tsel.centerOfMass();
			    # finding associated BIN
			    # location of X
			    x = COM[0]; y = COM[1];
			    #print "### BOTTOM leaflet [{}]###".format(num_frm);
			    #print "\tCOM: x={}, y={}".format(x,y);
			    tmp = stanalyzer.count_intervals2(x, BIN_X);
			    loc_x = tmp.index(1);
			    tmp = stanalyzer.count_intervals2(y, BIN_Y);
			    loc_y = tmp.index(1);
			    # count the frequency
			    bin_idx = loc_x * len(BIN_Y) + loc_y;
			    tmp_btmDNST[bin_idx][2] = tmp_btmDNST[bin_idx][2] + 1.0;
			    #print "\tBIN: x={}, y={}, freq={}".format(BIN_btm[bin_idx][0], BIN_btm[bin_idx][1], tmp_btmDNST[bin_idx][2]);
	    
	    # normalizing based on the number of frame
	    #print "#### Frame SUM ###"
	    if top_flag > 0:
		BIN_top = np.array(BIN_top);
		tmp_topDNST = np.array(tmp_topDNST);
		BIN_top[:,2] = BIN_top[:,2] + tmp_topDNST[:,2] / num_frm;
	    
	    if btm_flag > 0:
		BIN_btm = np.array(BIN_btm);
		tmp_btmDNST = np.array(tmp_btmDNST);
		BIN_btm[:,2] = BIN_btm[:,2] + tmp_btmDNST[:,2] / num_frm;

	#print "### Trajectory SUM ###"
	mr = 0.75;
	if top_flag > 0:
	    BIN_top[:,2] = BIN_top[:,2] / len(ST_trajectoryFile);
	    top_max = np.float(np.max(BIN_top[:,2])) * mr;
	    top_min = np.float(np.min(BIN_top[:,2])) * mr;
	    top_intv = top_max / 4.0;
	    topIntv = [];
	    topIntv.append(0);
	    tmp =0;
	    while(1):
		tmp = tmp + top_intv;
		topIntv.append(tmp);
		if tmp >= top_max:
		    break;
	    
	if btm_flag > 0:
	    BIN_btm[:,2] = BIN_btm[:,2] / len(ST_trajectoryFile);
	    btm_max = np.float(np.max(BIN_btm[:,2])) * mr;
	    btm_min = np.float(np.min(BIN_btm[:,2])) * mr;
	    btm_intv = btm_max / 4.0;
	    btmIntv = [];
	    btmIntv.append(0);
	    tmp =0;
	    while(1):
		tmp = tmp + top_intv;
		btmIntv.append(tmp);
		if tmp >= btm_max:
		    break;
			
	########################################
	###### Writing final output below ######
	########################################
	#print "Defining Output files";
	ftop = '{0}/top_{1}'.format(ST_out_dir, ST_outFile);
	fid_ftop = open(ftop, 'w');
	fbtm = '{0}/btm_{1}'.format(ST_out_dir, ST_outFile);
	fid_fbtm = open(fbtm, 'w');
    
	# pick one of output file names for DB usage
	out_file = ftop;
	
	# writing comments '#' is considered as a comment in GNUPlot
	#print "Writing output files";
	cmt = "#X_axis\tY_axis\tDensity\n";
	fid_ftop.write(cmt);
	fid_fbtm.write(cmt);
	
	x_cnt = 0;
	for i in range(len(BIN_top)):
	    x_cnt = x_cnt + 1;
	    if top_flag > 0:
		out_data_top = "{}\t{}\t{}\n".format(BIN_top[i,0], BIN_top[i,1], BIN_top[i,2]);
		fid_ftop.write(out_data_top);
	    if btm_flag > 0:
		out_data_btm = "{}\t{}\t{}\n".format(BIN_btm[i,0], BIN_btm[i,1], BIN_btm[i,2]);
	        fid_fbtm.write(out_data_btm);
	    if (x_cnt % len(BIN_Y)) == 0:
		fid_ftop.write("\n");
		fid_fbtm.write("\n");
	fid_ftop.close();
	fid_fbtm.close();
	
	########################################
	########### Drawing graphs #############
	########################################
	# Writing Gnuplot script
	#print "Drwaing plot"
	outScr = '{0}/gplot{1}.gpl'.format(ST_out_dir, ST_para_idx);
	outImg  = '{0}{1}.png'.format(exe_file[:len(exe_file)-3], ST_para_idx);
	imgPath = "{0}/{1}".format(ST_out_dir, outImg);
	fid_out = open(outScr, 'w');
	gScript = """set terminal png enhanced \n""";
	gScript = gScript + "set output '{0}'\n".format(imgPath);
	gScript = gScript + "set multiplot layout 2, 1 title '2D lipid density profile'\n";
	
	gScript = gScript + """set xtics offset 0,0.5; unset xlabel\n""";
	gScript = gScript + """set label 1 'Top' at graph 0.01, 0.95 font ',8'\n""";
	gScript = gScript + """set ylabel 'Density' offset 0,-8\n""";
	gScript = gScript + """set pm3d map\n""";
	gScript = gScript + """set palette defined (0 "white", {} "blue", {} "green", {} "red")\n""".format(topIntv[1], topIntv[2], topIntv[3]);
	gScript = gScript + """set cbrange [0:{}]\n""".format(top_max);
	gScript = gScript + """set cbtic {}\n""".format(top_intv);
	#gScript = gScript + """splot "{0}" using 1:2:3 with dots palette notitle\n""".format(ftop);
	gScript = gScript + """splot "{0}" notitle\n""".format(ftop);
	
	gScript = gScript + """set xtics offset 0,0.5; unset xlabel; unset ylabel\n""";
	gScript = gScript + """set label 1 'Bottom' at graph 0.01, 0.95 font ',8'\n""";
	gScript = gScript + """set xlabel 'Distance' offset 0,1\n""";
	gScript = gScript + """set pm3d map\n""";
	
	#gScript = gScript + """set palette defined (0 "white", {} "blue", {} "green", {} "red")\n""".format(btmIntv[1], btmIntv[2], btmIntv[3]);
	#gScript = gScript + """set cbrange [0:{}]\n""".format(btm_max);
	#gScript = gScript + """set cbtic {}\n""".format(btm_intv);
	# to make same map with top leaflet
	gScript = gScript + """set palette defined (0 "white", {} "blue", {} "green", {} "red")\n""".format(topIntv[1], topIntv[2], topIntv[3]);
	gScript = gScript + """set cbrange [0:{}]\n""".format(top_max);
	gScript = gScript + """set cbtic {}\n""".format(top_intv);
	#gScript = gScript + """splot "{0}" using 1:2:3 with dots palette notitle\n""".format(fbtm);
	gScript = gScript + """splot "{0}" notitle\n""".format(fbtm);
	
	gScript = gScript + "unset multiplot\n";
	fid_out.write(gScript);
	fid_out.close();
	
	# Drawing graph with gnuplot
	subprocess.call(["gnuplot", outScr]);
	
	# gzip all reaults
	outZip = "{0}project_{1}_{2}{3}.tar.gz".format(ST_OUTPUT_HOME, ST_prj_pkey, fName[1], ST_para_idx);
	subprocess.call(["tar", "czf", outZip, ST_out_dir]);
	
	# Update values into gui_outputs
	conn = sqlite3.connect(ST_DB_FILE);
	c    = conn.cursor();
	query = """UPDATE gui_outputs SET status = "Complete", img="{0}", txt="{1}", gzip="{2}" WHERE id = {3}""".format(imgPath, out_file, outZip, pk_output);
	c.execute(query);
	conn.commit();
	conn.close();
	
    
    
    ######################################## PLEASE DO NOT MODIFY BELOW THIST LINE!!!! ############################################
    # update gui_parameter & gui_job table when job completed
    etime = datetime.now().strftime("%Y-%m-%d %H:%M:%S");
    conn = sqlite3.connect(ST_DB_FILE);
    c    = conn.cursor();
    for i in range(len(para_pkey)):
	query = """UPDATE gui_parameter SET status = "COMPLETE" WHERE id = {0}""".format(para_pkey[i]);
	c.execute(query);
	conn.commit();
    
    # update gui_job if every status in gui_parameter are COMPLETE
    query = """SELECT DISTINCT(status) FROM gui_parameter WHERE job_id = {0}""".format(ST_job_pkey[0]);
    c.execute(query);
    ST = c.fetchall();
    
    if (len(ST) == 1) and (ST[0][0] == "COMPLETE"):
	etime = datetime.now().strftime("%Y-%m-%d %H:%M:%S");
	query = """UPDATE gui_job SET status = "COMPLETE", etime = "{0}" WHERE id = {1}""".format(etime, ST_job_pkey[0]);
	c.execute(query);
	conn.commit();
    
	# making tar file
	outZip = "{0}project_{1}.tar.gz".format(ST_OUTPUT_HOME, ST_prj_pkey[0]);
	subprocess.call(["tar", "czf", outZip, ST_OUTPUT_HOME]);
    
    conn.close();

#///////////////////////////////////////////////////////////////////////////
# Finalizing  job
# -- Use following codes to make your own function
#///////////////////////////////////////////////////////////////////////////
except:
    # update gui_parameter & gui_job table when job failed
    print "ERROR OCCURRED!"
    etime = datetime.now().strftime("%Y-%m-%d %H:%M:%S");
    conn = sqlite3.connect(ST_DB_FILE);
    c    = conn.cursor();
    for i in range(len(para_pkey)):
        query = """UPDATE gui_parameter SET status = "FAILED" WHERE id = {0}""".format(para_pkey[i]);
        c.execute(query);
        conn.commit();
    query = """UPDATE gui_job SET status = "INTERRUPTED" WHERE id = {0}""".format(ST_job_pkey[0]);
    c.execute(query);
    conn.commit();
    
    query = """UPDATE gui_outputs SET status = "Failed" WHERE id = {0}""".format(pk_output);
    c.execute(query);
    conn.commit();

    conn.close();

#///////////////////////////////////////////////////////
# print gui_job and gui_parameter table
#///////////////////////////////////////////////////////
stime = datetime.now().strftime("%Y-%m-%d %H:%M:%S");
conn = sqlite3.connect(ST_DB_FILE);
c    = conn.cursor();

#print "========= gui_job ==========="
query = "SELECT id, name, proj_id, anaz, status, output, stime, etime FROM gui_job";
c.execute(query);
job = c.fetchall();
query = "SELECT id, job_id, anaz, para, val, status FROM gui_parameter";
c.execute(query);
PR = c.fetchall();
conn.close();

