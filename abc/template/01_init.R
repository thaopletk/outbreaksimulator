setwd("C:/TK/outbreaksimulator/abc/template")
config_file <- "config_HPAI"

# ABC initialisation script for Hunter *EXAMPLE* data

library(dplyr)
library(Rcpp)
library(BH)
library(readxl)
library(yaml)
source("../../functions_pre-abc.R")
source("../../functions_post-abc.R")

as_vector <- function(x) {
    if(is.list(x)) { as.numeric(unlist(x)) } else x
}

'------ Run via shell script ------'
# get the input passed from the shell script
args <- commandArgs(trailingOnly = TRUE)
str(args)
cat(args, sep = "\n")

# test if there are three arguments: if not, return an error (ADJUST IF USING YAML)
if (length(args) != 1) {
    stop("Exactly 1 argument must be supplied (input file).\n", call. = FALSE)
} else {
    print(paste0("Arg input: ", args[1], sep = ' ')) #, args[2], args[3]
    config_file = args[1]
}

# read config file
config <- yaml::read_yaml(paste0("../../config/", config_file, ".yaml")) # read_yaml("abc_config.yaml")

# read priors
priors_file = config$general$priors_file
priors <- read.csv(paste0("../../config/", priors_file)) 

# create folder to contain abc output
ifelse(!dir.exists('Out'), dir.create('Out'), FALSE) 

# set file location to save setup info for ABC (saved at the end of this script) (!!!)
setup.file = config$general$setup_file #"Out/Hunter_data_ABC.RData"

# load data
dat_file = config$general$data_file #"Data/dat_Hunter.csv" 
dat <- read.csv(paste0("../../", dat_file), header = TRUE)
check_status <- which(dat$status == "NIL" & !is.na(dat$notification_date))
if (length(check_status) > 0) {dat$status[check_status] <- "IP"}

# date format
date_format = config$general$date_format 

# want to plot data?
plots = config$general$plots 

# want to reproduce the results?
reproduce = config$general$reproduce

"------- TK simulator paras --------"
# map size (only for TK's simulator)
previous_t_point <- config$TK$t_point
previous_DDD <- config$TK$DDD
previous_vaccine <- config$TK$vaccine
xrange <- config$TK$xrange
yrange <- config$TK$yrange
if (length(previous_t_point) != length(previous_DDD) ||
    length(previous_t_point) != length(previous_vaccine)) {
    stop("previous_t_point, previous_DDD, and previous_vaccine must have the same length.")
}

previous_t_diff <- diff(c(0, previous_t_point)) # length of simulation
previous_policy <- ifelse(
    previous_DDD == "high" & previous_vaccine == FALSE,
    "fast DDD",
    ifelse(
        previous_DDD == "high" & previous_vaccine == TRUE,
        "fast DDD vaccination",
        ifelse(
            previous_DDD == "low" & previous_vaccine == FALSE,
            "slow DDD",
            ifelse(
                previous_DDD == "low" & previous_vaccine == TRUE,
                "slow DDD vaccination",
                NA_character_
            )
        )
    )
) 

"------- Setup sim params --------" # (!!!)
# model to use (!!!)
scenario = config$run_parameters$scenario # EI = 10, FMD = 20, etc.

# time lag in data (in days)
# t_lag <- config$run_parameters$t_lag # fit model to data up to t_today-t_lag

# dt_length
# dt.length <- config$run_parameters$dt_length #50 for EI, 125 for FMD

# Number of particles
N.particles <- config$run_parameters$n_particles #1000
n.cpus <- config$run_parameters$n_cpus #50 # this has to correspond to the no. of arrays you asked for in `02_stepx.slurm`, i.e.: #SBATCH --array=1-n.cpus

# Number of generations
G = config$run_parameters$n_generations 

# epsilon per gen/step (tolerance) 
if(!all(config$tolerance$temporal_tolerance_daily == "NA")){ # if set manually in .yaml; if NA, this is set automatically later
    temporal.tolerance.daily <-  as_vector(config$tolerance$temporal_tolerance_daily) 
}

# spatial
if(!all(config$tolerance$spatial_tolerance == "NA")){
    epsilon.spatial <- as_vector(config$tolerance$spatial_tolerance) #c(0.3, 0.4, 0.5, 0.6, 0.65, 0.675, 0.7, 0.725) # correlation R value
} else{
    if(G<=8){
        epsilon.spatial <- c(0.3, 0.4, 0.5, 0.6, 0.65, 0.675, 0.7, 0.725)[1:G]  
    } else {
        epsilon.spatial <- c(0.3, 0.4, 0.5, 0.6, 0.65, 0.675, 0.7, 0.725, 0.75, 0.775)[1:G]
    }
}

cell.reso = config$tolerance$cell_resolution # resolution for spatial target (number of cells length-wise)

# - check if spatial tolerance schedule and no. generations are equal (!!! process killed if not met)
if ( !length(epsilon.spatial) == G ){ 
    stop("Spatial tolerance schedule and no. generations do not match\n") # MT: also need to stop the whole slurm process from running... how?
}

# Priors
para.names = priors$param_name

## paras indexes and prior bounds (process should now be same for EI/FMD)
paras.index <- which(priors$estimated_param==T) # c(1,4,5,7,9,14,18) # list index of parameters we're estimating for EI
lm.low<-priors$lower_bound[paras.index] #c(1,0,0,0,-2,-2,0) # unif prior lower bound for params
lm.upp<-priors$upper_bound[paras.index] #c(20,0.02,0.02,20,2,2,1) # unif prior upper bound
cbind(priors$param_name[paras.index], lm.low, lm.upp)

paras.index.ratio <- which(priors$prior_type == 2) #paras on ratio scale (i.e., zeta1 is cattle relatively to sheep[reference])
para.names[paras.index.ratio]

paras.index.unif<-paras.index[which(!paras.index %in% paras.index.ratio)]
para.names[paras.index.unif]

# fixed params
paras.fixed <- which(priors$fixed_param==T) #c(2,3,6) # sigma_intra, gamma_intra and kernel type (index)
para.names[paras.fixed]
fixed.vals <- priors$value[paras.fixed] #c(1/1, 1/6,4)  # sigma_intra, gamma_intra and kernel type (values)

# import and prep data
to_epsg <- get_projected_epsg(dat$longitude[1], dat$latitude[1])

dat <- dat %>%
    crs_transform(dat = ., lon = "longitude", lat = "latitude", from = "epsg:4326", to = to_epsg) %>%
    mutate(
        across(any_of(c("clinical_date", "notification_date", "recovery_date", 
                        "removal_date", "vacc_date", "report_date")), 
               ~ as.Date(.x, format = date_format)),

        x_km = round(changed_lon/1000, 3), 
        y_km = round(changed_lat/1000, 3)
    )

# last day of simulation = (!!!)
t_max = config$run_parameters$t_max 
t_start=1; t_end = t_max # will get rid of one eventually...
t_today = eval(parse(text = config$run_parameters$t_today)) # days from the first confirmed case
if(!config$run_parameters$date0 == "NA") {
    date0 = as.Date(config$run_parameters$date0, date_format)
} else {
    date0_offset = config$run_parameters$date0_offset
}

#calculate distance matrix with cpp function
Sys.setenv("PKG_CXXFLAGS"="-std=c++14") # set up cpp
sourceCpp("distmat.cpp")
distmat<-round(distmat_cppfunc(x=as.numeric(dat$x_km), y=as.numeric(dat$y_km), coord_type="cartesian")$distmat,3)

"------- Save setup file --------"
# with sim param setup stored
save.image(setup.file)
dput(setup.file, 'Out/setup.file.txt')

# initialise with g = 1
g <- 1
dput(g, 'Out/g.txt')
