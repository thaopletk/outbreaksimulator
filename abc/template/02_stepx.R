# load("C:/TK/outbreaksimulator/abc/template/Out/Outputs.RData"); task.id=1

library(dplyr)
"------- 0 Load data and params --------"
date_to_string <- function(x) {
    if (is.na(x)) { return("NA") }
    format(x, "%d/%m/%Y")
}

setup.file = dget('Out/setup.file.txt')
setup.file
load(setup.file)

g <- dget('Out/g.txt')
g

if(g>1){
  load(paste0("Out/smc.abc.g",g-1,".postclust.RData")); g<-g+1
}
g

task.id<-as.numeric(Sys.getenv('SLURM_ARRAY_TASK_ID'))
task.id
sim_dir <- paste0('task',task.id)
ifelse(!dir.exists(sim_dir), dir.create(sim_dir), FALSE)
ifelse(!dir.exists(paste0(sim_dir,"/03_outbreak_detection")), 
       dir.create(paste0(sim_dir, "/03_outbreak_detection")), FALSE)
file.copy(
    "../../config/approx_known_data_03_outbreak_detection.csv",
    file.path(sim_dir, "03_outbreak_detection"),
    overwrite = TRUE
)

"------- 1 Set up environment --------"
library(reticulate); use_python(Sys.which("python"), required = TRUE)
v06_functions <- import_from_path("v06_functions", path = "C:/TK/outbreaksimulator/scenarios")
Premises <- import("simulator.premises")$Premises
DiseaseSimulation <- import("simulator.disease_simulation")$DiseaseSimulation
np <- import("numpy")
pd <- import("pandas")
pickle <- import("pickle")
shapely_geometry <- import("shapely.geometry")
Polygon <- shapely_geometry$Polygon
builtins <- import_builtins()
itertools <- import("itertools")
os <- import("os")

###################################
seed<-1e5+task.id
set.seed(seed)

i<-1 # for calculating no accepted particles
k<-1 # for calculating acceptance rate
N.particles.g<-length(grep(paste0('^gen_',g,'_task_'),list.files(path = "Out")))

"------- 2 Excecute ABC sampling --------"
while(N.particles.g < N.particles){ # While the number of accepted particles is less than N_particles
    
    # track particle acceptance; set to 0 first
    accepted <- 0 
    
    # create empty param list first
    if (scenario == 10 || scenario == 20) {
        paras<-list(beta_intra = NA, #within-farm beta transmission rate (S to E)
                    sigma_intra = NA, #within-farm 1/latent period transmission rate (E to I)
                    gamma_intra = NA, #within-farm 1/infectious duration transmission rate (I to R)
                    
                    alpha = NA, #background transmission rate
                    beta0 = NA, #baseline transmission rate
                    
                    kernel_type = NA, #1:exponential, 2:power_law, 3:cauchy, 4:cauchy_dist
                    psi = NA, #spatial kernel shape para
                    rho0 = NA, #spatial kernel shape para2 (estimated from MLE)
                    
                    zeta = NA, #the infectivity of all animals combined (i.e., for EI - single species)
                    zeta_1 = NA, #the infectivity of cattle to sheep
                    zeta_2 = NA, #the infectivity of pigs
                    zeta_3 = NA, #the infectivity of others
                    
                    chi = NA, # an index of the counts per species
                    
                    xi = NA,  #the susceptibility of all animals combined (i.e., for EI - single species)
                    xi_1 = NA, #the susceptibility of cattle from sheep
                    xi_2 = NA, #the susceptibility of pigs
                    xi_3 = NA, #the susceptibility of others
                    
                    theta = NA #vaccination effectiveness
                    
        )
    } else if (scenario == 30) {
        paras<-list(beta_intra = NA, #within-farm beta transmission rate (S to E)
                    sigma_intra = NA, #within-farm 1/latent period transmission rate (E to I)
                    gamma_intra = NA, #within-farm 1/infectious duration transmission rate (I to R)
                    
                    alpha = NA, #background transmission rate
                    beta0 = NA, #baseline transmission rate
                    
                    kernel_type = NA, #1:exponential, 2:power_law, 3:cauchy, 4:cauchy_dist
                    psi = NA, #spatial kernel shape para
                    rho0 = NA, #spatial kernel shape para2 (estimated from MLE)
                    
                    zeta = NA, #the infectivity of all animals combined (i.e., for EI - single species)
                    zeta_1 = NA, #the infectivity of cattle to sheep
                    zeta_2 = NA, #the infectivity of pigs
                    zeta_3 = NA, #the infectivity of others
                    
                    chi = NA, # an index of the counts per species
                    
                    xi = NA,  #the susceptibility of all animals combined (i.e., for EI - single species)
                    xi_1 = NA, #the susceptibility of cattle from sheep
                    xi_2 = NA, #the susceptibility of pigs
                    xi_3 = NA, #the susceptibility of others
                    
                    theta = NA, #vaccination effectiveness
                    
                    add_c = NA, # recruitment of cattle
                    add_v = NA, # vector population recruitment
                    mu_c = NA, # natural death rate of cattle 
                    mu_v = NA, # natural death rate of vectors
                    
                    a1 = NA, # parameter for biting rate
                    a2 = NA, # parameter for biting rate
                    a3 = NA, # lower limit of temp
                    a4 = NA, # upper limit of temp
                    v_vc = NA, # probability of transmission from vector to cattle
                    v_cv = NA, # probability of transmission from cattle to vector
                    d_v = NA, # vector density
                    
                    omega = NA, # waning rate
                    mu_lsd = NA, # mortality rate of LSD
                    trans = NA, # virus survival rate on vectors
                    
                    scaling_c = NA, # scaling factor for transmission rate of cattle
                    scaling_v = NA # scaling factor for transmission rate of vector
        )
    } else if (scenario == 40) {
        paras<-list(beta_wind = NA,
                    beta_animal = NA,
                    latent_period = NA,
                    infectious_period = NA,
                    preclinical_period = NA,
                    lab_test_sensitivity = NA,
                    clinical_test_sensitivity = NA,
                    cull_delay = NA,
                    contact_tracing_delay = NA,
                    lab_test_delay = NA,
                    clinical_delay = NA,
                    vaccination_delay = NA,
                    clinical_reporting_threshold = NA,
                    prob_report = NA,
                    prob_report_commercial = NA,
                    prob_report_backyard = NA,
                    r_wind = NA
        )
    }
    
    # ----- (a) Draw a set of parameter values -----
    if(g==1){ # first step/gen
        # Sample from prior distributions
        # fill param list with values
        paras[paras.fixed] <- fixed.vals # fixed intra values
        
        #sample paras with uniform priors    
        paras[paras.index.unif] <- sapply(which(paras.index %in% paras.index.unif), 
                                          function(x) runif(1,lm.low[x],lm.upp[x])) # sampling happens here
        #cbind(para.names[paras.index], lm.low, lm.upp)
        #sample any ratio paras on log scale
        if(length(paras.index.ratio)>0){
            paras[paras.index.ratio] <- 10^(sapply(which(paras.index %in% paras.index.ratio), 
                                                   function(x) runif(1,lm.low[x],lm.upp[x])))
        }
        
    } else { # second step/gen 2 onwards
        #  Select particle from previous generation
        p <- sample(seq(1, N.particles), 1, prob = w.old)
        par <- vector()
        for(j in 1:length(paras.index)){ 
            
            par[j] <- lm.upp[j] + 1 #start out above the priors, resample until get a value within bounds
            #  sample for new parameter values
            while((par[j]<lm.low[j]) | (par[j]>lm.upp[j]) ){
                
                if(paras.index[j] %in% paras.index.unif){par[j]<-rnorm(1, theta.old[p,j], sqrt(2*tau.var.old[j]))}
                if(paras.index[j] %in% paras.index.ratio){par[j]<-rnorm(1, log10(theta.old[p,j]), sqrt(2*tau.var.old[j]))}
            }
            if(paras.index[j] %in% paras.index.ratio){par[j] <- 10^par[j]}
        } 

        # fill param list with values
        paras[paras.fixed] <- fixed.vals # fixed intra values
        paras[paras.index] <- sapply(1:length(paras.index), function(x) par[x]) # fill 
        
    } # end of else
    
    # ----- (b) data reconstruction -----
    dat <- dat %>%
        mutate(exposure_date = case_when(!is.na(clinical_date) ~ 
                                             clinical_date - paras$preclinical_period,
                                         TRUE ~ clinical_date))
    
    if(!exists("date0")) {
        date0 = min(dat$exposure_date, na.rm=T) - date0_offset
    }
    
    dat <- dat %>%
        mutate(t_c = as.numeric(clinical_date - date0),
               t_n = as.numeric(notification_date - date0),
               t_e = as.numeric(exposure_date - date0),
               t_i = t_e + paras$latent_period,
               t_r = as.numeric(recovery_date - date0),
               t_d = as.numeric(removal_date - date0),
               t_v = as.numeric(vacc_date - date0)) %>%
        mutate(t_i = if_else(t_i > t_c, t_c, t_i))
    
    t_detect <- min(dat$t_n, na.rm=T); t_detect
    if ( is.na(t_today) ) {
        t_today <- max(dat$t_n, na.rm=T) + 1 # t_today is the day after the last notification
    } else {
        t_today <- t_today + t_detect # we put t_today (t_detect based; e.g., 3 weeks after t_detect)
    }
    
    dat_today <- dat 
    
    id<-which(dat$t_e<t_detect); length(id) 
    
    dat$ip<-NA
    dat$ip[id]<-1:length(id)
    dat$status<-"NIL"
    dat$status[id]<-"IP"
    
    # non-IPs
    dat$t_c[-id]<-NA
    dat$t_n[-id]<-NA
    dat$t_e[-id]<-NA
    dat$t_i[-id]<-NA
    dat$t_r[-id]<-NA
    dat$t_d[-id]<-NA
    N = nrow(dat)
    dat$id_t<-1:N
    
    E_t <- dat$id_t[id]
    id <- which(dat$t_i < t_detect)
    I_t <- id
    id <- match(I_t, E_t)
    if(length(id)>0){E_t <- E_t[-id]}; E_t
    R_t <- dat$id_t[which(dat$t_r < t_detect)]
    
    # remove R_t from I_t
    id<-match(R_t, I_t)
    if(length(id)>0){I_t<-I_t[-id]}
    
    # depoped
    D_t <- dat$id_t[which(dat$t_d < t_detect)]
    D <- length(D_t)
    
    id<-sort(c(E_t, I_t, R_t, D_t))
    S_t <- dat$id_t[-id]
    
    S = length(S_t)
    E = length(E_t)
    I = length(I_t)
    R = length(R_t)
    
    # ----- (c) set targets -----
    E.obs <- sapply(t_detect:t_today, function(x) length(which(x == dat_today$t_e))) #exposures (infections)
    I.obs <- sapply(t_detect:t_today, function(x) length(which(x == dat_today$t_i))) # onset of infectiousness
    C.obs <- sapply(t_detect:t_today, function(x) length(which(x == dat_today$t_c))) # clinical onset
    N.obs <- sapply(t_detect:t_today, function(x) length(which(x == dat_today$t_n))) # notification
    R.obs <- sapply(t_detect:t_today, function(x) length(which(x == dat_today$t_r))) # recovery
    D.obs <- sapply(t_detect:t_today, function(x) length(which(x == dat_today$t_d))) # depopulation
    
    target.temporal <- data.frame(t = t_detect:t_today,
                                  E = E.obs,
                                  I = I.obs,
                                  C = C.obs,
                                  N = N.obs,
                                  R = R.obs,
                                  D = D.obs)
    
    if(sum(config$tolerance$temporal_tolerance_daily == "NA")){ # if set as NA in .yaml (read as string)
        if(G<=8){
            temporal.tolerance.daily <- mean(target.temporal$E) * 3 * 
                round(exp(seq(log(1), log(0.12), length.out = 8)), 4)[1:G] # geometric decay
        }else{
            temporal.tolerance.daily <- mean(target.temporal$E) * 3 * 
                round(exp(seq(log(1), log(0.12), length.out = G)), 4)
        }
    }
    epsilon.temporal <- ceiling( temporal.tolerance.daily * length(t_detect:t_today) ) ; epsilon.temporal
    
    x_min = round(min(dat_today$x_km) - 1, 0)
    x_max = round(max(dat_today$x_km) + 1, 0)
    y_min = round(min(dat_today$y_km) - 1, 0)
    y_max = round(max(dat_today$y_km) + 1, 0)
    
    # exposures (infections) per cell at t_today
    dat_ip <- dat_today[which(dat_today$t_e %in% t_detect:t_today),] # infections (exposures) at t_today (minus t_lag)
    
    target.spatial <- dat_ip %>% 
        mutate(
            cut_x = cut(x_km, breaks = seq(x_min, x_max, (x_max-x_min)/cell.reso), include.lowest = T),
            cut_y = cut(y_km, breaks = seq(y_min, y_max, (y_max-y_min)/cell.reso), include.lowest = T)) %>%
        count(cut_x, cut_y, .drop = F) %>%# number of infecteds per cell (final size)
        mutate(cell = 1:length(n)) %>%
        select(cell, n) 
    
    n_premises_cell <- dat_today %>% # no. of premises per cell
        mutate(
            cut_x = cut(x_km, breaks = seq(x_min, x_max, (x_max-x_min)/cell.reso), include.lowest = T),
            cut_y = cut(y_km, breaks = seq(y_min, y_max, (y_max-y_min)/cell.reso), include.lowest = T)) %>%
        count(cut_x, cut_y, .drop = F) %>%# number of infecteds per cell (final size)
        select(n)
    
    cell_index <- which(n_premises_cell$n >0)
    
    # ----- (d) create pickle objects -----

    # First IP
    first_ip_idx <- which.min(dat$t_e)
    first_ip_id <- dat$id[first_ip_idx]
    # Exposed premises
    is_exposed <- !is.na(dat$exposure_date)
    properties <- vector("list", nrow(dat))
    
    for (i in seq_len(nrow(dat))) {
        
        row <- dat[i, ]
        empty_polygon <- Polygon()
        
        coordinates <- np$array(
            c(row$longitude, row$latitude),
            dtype = "float64"
        )
        
        p <- Premises(
            num_animals = 0L,
            movement_freq = 1L,
            coordinates = coordinates,
            neighbourhood = list(),
            property_polygon = empty_polygon,
            property_polygon_puffed = empty_polygon,
            animal_type = "chicken"
        )
        
        # 1. sim_id
        p$sim_id <- as.integer(row$id)
        
        # 2. id
        p$id <- as.integer(row$id_t)
        
        # 3-7. dates
        p$exposure_date <- date_to_string(row$exposure_date)
        p$clinical_date <- date_to_string(row$clinical_date)
        p$notification_date <- date_to_string(row$notification_date)
        p$recovery_date <- date_to_string(row$recovery_date)
        p$removal_date <- date_to_string(row$removal_date)

        # 8-11. Population / area
        n_total <- as.numeric(row$n_total)
        area_h <- as.numeric(row$area_h)
        p$size <- as.integer(n_total)
        p$known_birds <- as.integer(n_total)
        
        # area_h can be NA
        if (is.na(area_h)) {
            p$area <- NA_real_
            p$known_area <- NA_real_
        } else {
            p$area <- area_h
            p$known_area <- area_h
        }
        
        # 12-14. Coordinates
        p$coordinates <- np$array(
            c(row$longitude, row$latitude),
            dtype = "float64"
        )
        
        p$x <- np$float64(row$longitude)
        p$y <- np$float64(row$latitude)
        
        # animal_type
        p$animal_type <- "chicken"
        
        # status
        if (i == first_ip_idx) {p$status <- "SP"} else {p$status <- "NA"}
        
        # infection_status
        if (is_exposed[i]) {p$infection_status <- 1L} else {p$infection_status <- 0L}
        
        # case information
        if (i == first_ip_idx) {
            p$case_id <- 1L
            p$case_created_date <-
                date_to_string(row$clinical_date)
            p$clinical_report_outcome <- TRUE
        } else {
            p$case_id <- np$nan
            p$case_created_date <- np$nan
            p$clinical_report_outcome <- np$nan
        }

        # Infection quantities
        p$cumulative_infections <- as.integer(n_total)
        p$number_infected <- as.integer(n_total)
        
        # Clinical / infectious proportions
        has_clinical <- !is.na(row$clinical_date)
        if (has_clinical) {
            p$prop_clinical <- 1.0
            p$prop_infectious <- 1.0
        } else {
            p$prop_clinical <- 0.0
            p$prop_infectious <- 0.0
        }

        # Shed information
        p$num_sheds <- 1L
        p$known_sheds <- 1L
        sheds <- dict()
        sheds[[1L]] <- dict()
        p$sheds <- sheds

        # Chicken capacity
        chicken_capacity <- if (n_total == 0) {
            100
        } else {
            n_total * 1.1
        }
        
        p$chicken_capacity <- as.integer(chicken_capacity)
        p$approx_chickens_per_shed <- as.integer(chicken_capacity)
        
        # Region / state
        p$region <- ""
        p$state <- "New South Wales"
        
        # Fields explicitly set to None
        p$QLD_property_type <- NULL
        p$address <- NULL
        p$chickens <- NULL
        p$day_of_last_lab_test <- NULL
        p$eggs_fertilised <- NULL
        p$location <- NULL
        p$radius <- NULL
        
        # Empty / NA string fields
        p$cluster <- "NA"
        p$county <- "NA"
        p$ip <- "NA"
        p$vacc_date <- "NA"
        p$housing_type <- "NA"
        p$type <- "NA"
        p$data_source <- ""
        
        # Movement
        p$allowed_movement <- dict()
        p$allowed_movement_details <- dict()
        p$movement_neighbours <- dict()
        p$max_daily_movements <- 1L
        p$movement_frequency <- 1L
        p$movement_probability <- 0L
        p$movement_prop_animals <- 0L
        p$movement_start_day <- 0L
        p$neighbourhood <- list()
        p$total_neighbours <- 0L

        # Other fields
        p$animals <- dict()
        p$cull_delay <- 0L
        p$culled_on_suspicion <- FALSE
        p$culled_status <- 0L
        p$custom_info <- dict()
        p$reported_status <- FALSE
        p$undergoing_testing <- FALSE
        p$vaccinate_delay <- 0L
        p$vaccination_status <- 0L
        p$accepts_hatchlings <- FALSE
        p$eggs <- 0L
        
        # Empty polygons
        p$polygon <- Polygon()
        p$puffed_poly <- Polygon()
        p$puffed_poly_area <- 0.0

        properties[[i]] <- p
    }

    properties_py <- r_to_py(properties)
    pickle_path <- paste0(sim_dir,"/03_outbreak_detection/properties_03_outbreak_detection")
    con <- builtins$open(pickle_path, "wb")
    pickle$dump(
        properties_py,
        con
    )
    con$close()
    
    
    movement_records <- pd$DataFrame(
        columns = c(
            "day",
            "date",
            "from",
            "to",
            "entity",
            "quantity",
            "facility_type_1",
            "facility_type_2",
            "report"
        )
    )
    diseaseoutbreak <- DiseaseSimulation$`__new__`(DiseaseSimulation)
 
    diseaseoutbreak$time <- as.integer(t_detect)
    diseaseoutbreak$movement_records <- movement_records
    diseaseoutbreak$beta_wind <- dict(chicken = paras$beta_wind)
    diseaseoutbreak$beta_animal <- dict(chicken = paras$beta_animal)
    diseaseoutbreak$latent_period <- dict(chicken = paras$latent_period)
    diseaseoutbreak$infectious_period <- dict(chicken = paras$infectious_period)
    diseaseoutbreak$preclinical_period <- dict(chicken = paras$preclinical_period)
    diseaseoutbreak$r_wind <- paras$r_wind
    diseaseoutbreak$clinical_reporting_threshold <- paras$clinical_reporting_threshold
    diseaseoutbreak$prob_report <- paras$prob_report
    diseaseoutbreak$prob_report_commercial <- paras$prob_report_commercial
    diseaseoutbreak$prob_report_backyard <- paras$prob_report_backyard
    diseaseoutbreak$vax_modifier <- 0.6
    diseaseoutbreak$combined_narrative <- list()
    diseaseoutbreak$xlims <- xrange
    diseaseoutbreak$ylims <- yrange
    diseaseoutbreak$plotting <- TRUE
    diseaseoutbreak$folder_path <- file.path(getwd(),"Out",paste0("pickle",task.id))
    diseaseoutbreak$unique_output <- paste0("pickle",task.id)
    diseaseoutbreak$job_manager <- NULL
    diseaseoutbreak$total_culled_animals <- 0L
    diseaseoutbreak$controlzone <- dict()
    diseaseoutbreak$contacts_for_plotting <- dict()
    diseaseoutbreak$daily_statistics <- dict()
    diseaseoutbreak$first_detection_day <- t_detect
    diseaseoutbreak$case_id_counter <- 1L
    diseaseoutbreak$notified_iter <- itertools$count(1L)
    
    pickle_path <- paste0(sim_dir,"/03_outbreak_detection/outbreakobject_03_outbreak_detection")
    con <- builtins$open(pickle_path,"wb")
    pickle$dump(
        diseaseoutbreak,
        con
    )
    con$close()

    # ----- (e) simulate -----
    
    
    result <- v06_functions$run_auto_strategies_ABC(
        state = "NSW",
        previous_unique_output =  "03_outbreak_detection",
        previous_output_suffix_int = 3L,
        total_days_to_run_for = as.integer(previous_t_diff[1]),
        create_download_folder = TRUE,
        download_folder_name = paste(
            "day",
            as.integer(previous_t_point[1]),
            gsub(" ", "_", previous_policy[1]),
            sep = "_"
        ),
        strategy = previous_policy[1],
        base_folder = file.path(getwd(),paste0("task", task.id))
    )
    
    
    
    result <- v06_functions$run_auto_strategies(
        state = "NSW",
        previous_unique_output = paste0('task',task.id,"/03_outbreak_detection"),
        previous_output_suffix_int = 3L,
        total_days_to_run_for = previous_t_diff[1],
        create_download_folder = TRUE,
        download_folder_name = paste("day",previous_t_point[1],gsub(" ", "_", previous_policy[1]),sep = "_"),
        strategy = previous_policy[1]
    )
    
    
    
    if(scenario == 10 || scenario == 20) {
        res <- tryCatch({
            dyn_sim_cppfunc(scenario=scenario, seed = seed, t = t_detect, t_max = t_end, 
                            n_total = as.numeric(dat$n_total),
                            n_sheep = as.numeric(dat$n_sheep), # might want to rename the arguments in the rcpp function to match
                            n_cattle = as.numeric(dat$n_cattle),
                            n_pigs = as.numeric(dat$n_pigs),
                            n_other = as.numeric(dat$n_other), # sum of other species can be done in data prep step
                            t_c = as.numeric(dat$t_c),
                            t_n = as.numeric(dat$t_n),
                            t_e = as.numeric(dat$t_e),
                            t_i = as.numeric(dat$t_i),
                            t_r = as.numeric(dat$t_r),
                            t_d = as.numeric(dat$t_d),
                            t_v = rep(9999, N), #set not to occur for FMD at this stage
                            x_km = as.numeric(dat$x_km),
                            y_km = as.numeric(dat$y_km),
                            area_h = as.numeric(dat$area_h),
                            S = S, E = E, I = I, R = R, D = D, N = N,
                            S_t = S_t, E_t = E_t, I_t = I_t, R_t = R_t, D_t = D_t,
                            paras = as.numeric(paras),
                            distmat = as.matrix(distmat),
                            h_list = vector("list", N),
                            dt_length = dt.length,
                            incubation_params = as.numeric(incubation_params),
                            latent_params = as.numeric(latent_params),
                            time_delays = as.matrix(time_delays),
                            print_prog = F)
        }, error = function(e) {
            message("Error in dyn_sim_cppfunc(): ", e$message)
            return(NULL)
        })
    } else if (scenario == 30) {
        res <- tryCatch({
            dyn_sim_cppfunc_lsd(scenario=scenario, seed = seed, t = t_detect, t_max = t_max,
                                farm_id = if(is.null(dat[[fid]])) integer(0) else dat[[fid]],
                                country = country,
                                n_total = as.numeric(dat$n_total),
                                n_ratio = as.numeric(dat$n_ratio),
                                n_vector = as.numeric(dat$vector),
                                t_c = as.numeric(dat$t_c),
                                t_n = as.numeric(dat$t_n),
                                t_e = as.numeric(dat$t_e),
                                t_i = as.numeric(dat$t_i),
                                t_r = as.numeric(dat$t_r),
                                t_d = as.numeric(dat$t_d),
                                t_v = as.numeric(dat$t_v),
                                x_km = as.numeric(dat$x_km),
                                y_km = as.numeric(dat$y_km),
                                S = S, E = E, I = I, R = R, D = D, N = N,
                                S_t = S_t, E_t = E_t, I_t = I_t, R_t = R_t, D_t = D_t,
                                paras = as.numeric(paras),
                                distmat = as.matrix(distmat),
                                days = temp$day,
                                temps = temp$temp_ave,
                                h_list = vector("list", N),
                                h_list_num = vector("list", N),
                                v_list = vector("list", N),
                                v_list_num = vector("list", N),
                                dt_length = dt.length,
                                incubation_params = as.numeric(incubation_params),
                                time_delays = as.matrix(time_delays),
                                print_prog = F)
        }, error = function(e) {
            message("Error in dyn_sim_cppfunc_lsd(): ", e$message)
            return(NULL)
        })
    }
    
    if (is.null(res)) next
    
    sim.temporal <-data.frame(t=t_start:t_end, 
                              E=sapply(t_start:t_end, function(x) length(which(x == res[['t_e']]))), #exposed (infected)
                              I=sapply(t_start:t_end, function(x) length(which(x == res[['t_i']]))), #infectious onset
                              C=sapply(t_start:t_end, function(x) length(which(x == res[['t_c']]))), #clinical onset
                              N=sapply(t_start:t_end, function(x) length(which(x == res[['t_n']]))), #notified
                              R=sapply(t_start:t_end, function(x) length(which(x == res[['t_r']]))), #recovered
                              D=sapply(t_start:t_end, function(x) length(which(x == res[['t_d']])))) #depopulated
    
    if(plots){ 
        plot(epic(dat_real$t_e, t_max), type='h', ylim=c(0,50), col='grey80')
        lines(sim.temporal$t, sim.temporal$E)
        abline(v=c(t_detect, t_today), col=c('red', 'blue'), lty=2)
    }
    
    
    # ----- (c) Calculate distances -----
    # warning: only fit data from t_detect to t_today, NOT all
    
    # temporal target
    distance.temporal <- sum( abs(sim.temporal$E[sim.temporal$t %in% t_detect:t_today] - target.temporal$E[target.temporal$t %in% t_detect:t_today]) )
    
    # spatial target
    sim.ip <- dat_today[which(res[["t_e"]] %in% t_detect:t_today),] 
    sim.spatial <- sim.ip %>% 
        mutate(
            cut_x = cut(x_km, breaks = seq(x_min, x_max, (x_max-x_min)/cell.reso), include.lowest = T),
            cut_y = cut(y_km, breaks = seq(y_min, y_max, (y_max-y_min)/cell.reso), include.lowest = T)) %>%
        count(cut_x, cut_y, .drop = F) %>%# number of infecteds per cell (final size)
        mutate(cell = 1:length(n)) %>%
        select(cell, n) 
    # only for cells containing a premise
    if(nrow(sim.ip)>0) {
        distance.spatial <- cor(target.spatial$n[cell_index], sim.spatial$n[cell_index]); distance.spatial
    } else {distance.spatial = 0}
    if (is.na(distance.spatial)){distance.spatial = 0} # handle error above
    
    #distance.spatial <- sum(abs(target.spatial$ip[cell_index] - sim.spatial$ip[cell_index])) # testing diff spatial criterion
    sim.t_e <- res[["t_e"]] #sim.t_i <- res[["t_i"]]
    rm(res); gc()
    
    # ----- (d) Accept/reject particle -----
    # If distances are less than their tolerances, particle is accepted 
    if(distance.temporal <= epsilon.temporal[g] &
       distance.spatial >= epsilon.spatial[g] &
       sum(sim.temporal$E[(t_detect + 1):t_today]) > 0){ # another criteria for accepting data fitting well to data
        print(paste0('Generation: ', g, ", task: ", task.id, ", particle: ", i))
        
        # store accepted particle components (inside the loop so can look at outputs without completing step)
        fn=paste0("Out/gen_",g,"_task_",task.id,"_particle_",i,"_iter_", k,".RData")
        save(list=c('seed','paras',
                    'distance.temporal','distance.spatial', #'distance.finalsize', 
                    'sim.temporal', 'sim.t_e','k' 
        ), file=fn)
        
        # Update counter      
        i <- i+1
        
        # track sample frequency and acceptance proportion
        accepted <- 1
        
    } # distance
    
    # ----- (f) Save output -----
    if (g == 1) {particle = NA} else {particle = p}
 
    # ----- (g) Print progress -----
    N.particles.g<-length(grep(pattern=paste0('^gen_',g,'_task_'),x=list.files(path="Out"))) # check no of accepted particles across entire slurm array
    
    acc_rate <- (i-1) / k # Calculate the acceptance rate   
    cat("current acceptance rate = ", acc_rate, "; N.particles = ", N.particles.g, "\r"); flush.console()
    k <- k + 1 # Update iteration counter  
    
} # while loop
"------- 02_stepx.R finished --------"