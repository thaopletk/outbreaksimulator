#!/bin/env bash
#SBATCH --job-name=setup
#SBATCH --output=setup.out
# The maximum running time of the job in days-hours:mins:sec
#SBATCH --time=0-05:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --mail-type=ALL #END,FAIL
#SBATCH --mail-user=simin.lee1@student.unimelb.edu.au

START=$(date "+%s")

module --force purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

#remove created virtual environment
if [ -d "venv" ]; then
    echo "Cleaning up existing venv to fix permission issues..."
    rm -rf venv
fi

echo "Creating fresh virtual environment..."
python -m venv venv

#Then activate with
. venv/bin/activate
#And then you will be in the virtual environment!

#python -m ensurepip --upgrade #if no pip
python -m pip install --upgrade pip
pip install -r requirements_v05.txt
pip install scipy matplotlib libpysal contourpy betapert
pip install openpyxl

echo "=========================================="
echo " Verifying Module Imports"
echo "=========================================="
python -c "
import numpy
import pandas
import geopandas
import betapert
import openpyxl
print('✅ All core packages imported successfully!')
"

END=$(date "+%s")
echo -e "\n"
TOTAL_SECONDS=$((END-START))
printf "ran in %02d:%02d:%02d\n" $((TOTAL_SECONDS/3600)) $((TOTAL_SECONDS%3600/60)) $((TOTAL_SECONDS%60))