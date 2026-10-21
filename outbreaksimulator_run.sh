#!/bin/env bash
#SBATCH --job-name=v06_lo
#SBATCH --output=v06_lo.out
# The maximum running time of the job in days-hours:mins:sec
#SBATCH --time=0-05:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --mail-type=ALL #END,FAIL
#SBATCH --mail-user=simin.lee1@student.unimelb.edu.au

#turn off bracketed text mode (create your own global config file)
#nano ~/.inputrc
#set enable-bracketed-paste off
#^X and restart terminal
START=$(date "+%s")


#cd outbreaksimulator/

module --force purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

#Initiate virtual environment using the following if not yet created 
# python -m venv venv
#Then activate with
. venv/bin/activate
#And then you will be in the virtual environment!
#  You can then deactivate with:
#deactivate

#python -m ensurepip --upgrade #if no pip
#python -m pip install --upgrade pip
#pip install -r requirements_v05.txt
#pip install numpy==2.2.6 scipy matplotlib libpysal contourpy
#pip install openpyxl
#python -c "from area import area; obj = {'type':'Polygon','coordinates':[[[-180,-90],[-180,90],[180,90],[180,-90],[-180,-90]]]}; print(area(obj))"

# clean up scernario folder then copy originals back across
#rm -rf scenarios/v06/*
#cp scenarios/originals/v06/*.* scenarios/v06/
#python scenarios/v06.py

#set seed for seeding outbreak in v06_functions.py L417-18, 449-50
rm -rf scenarios/v06_NSW/*
cp scenarios/originals/v06_NSW/*.* scenarios/v06_NSW/
python scenarios/v06_simon.py


END=$(date "+%s")
echo -e "\n"
TOTAL_SECONDS=$((END-START))
printf "ran in %02d:%02d:%02d\n" $((TOTAL_SECONDS/3600)) $((TOTAL_SECONDS%3600/60)) $((TOTAL_SECONDS%60))