import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))
import numpy as np
from shapely.geometry import Point
import csv
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output

# based from the fmdmodelling function FMD_ABM, but with modifications (e.g. around saving data at various time points)
def modified_FMD_ABM(params, plotting, folder_path, xrange = [150.2503,151.39695], yrange = [-32.61181, -31.60829],unique_output=""):
    total_culled = 0
    total_vaccinated = 0
    xlims=[round(xrange[0],2)-0.005,round(xrange[1],2)+0.005]
    ylims=[round(yrange[0],1)-0.05,round(yrange[1],1)+0.05]

    property_coordinates, adjacency_matrix, neighbour_pairs, neighbourhoods = spatial_setup.generate_properties(params['n'], params['r'], xrange, yrange) # uses the spatial-setup specific generator, rather than the fmdmodelling property generator; which means that it lacks property radii

    # initialise properties 
    properties = []
    for i in range(params['n']):
        properties.append(premises.Premises(params))
        properties[i].init_animals(params)
        properties[i].coordinates = property_coordinates[i]
        # properties[i].radius default to zero
        # properties[i].area default to 500
        properties[i].neighbourhood = neighbourhoods[i]
        properties[i].total_neighbours = len(properties[i].neighbourhood)

    
    output.save_data_properties([properties,property_coordinates, adjacency_matrix, neighbour_pairs, neighbourhoods],folder_path)

    # seed infection
    # property coordinates allocated at random, so can just seed the first property in each simulation 
    seed_property = 0
    seed_animal = 0
    properties[seed_property].infection_status = 1
    properties[seed_property].animals[seed_animal].status = 'infected'
    properties[seed_property].prop_infectious = 1/params['size']
    properties[seed_property].cumulative_infections = 1

    # initialise list of cumulative infections from each property - calculated for FOI every loop
    cumulative_infection_proportions = list(np.zeros(params['n']))
    cumulative_infection_proportions[seed_property] = properties[seed_property].cumulative_infections/properties[seed_property].size

    # infected_properties = 1
    # infected_proportions = list(np.zeros(params['n']))
    # infected_proportions[seed_property] = properties[seed_property].prop_infectious


    # set up some random initial vaccination
    # NOTE: may remove this
    for i, premise in enumerate(properties):
        if premise.infection_status !=1:
            premise.vaccination(params, params['initial_vaccination'], time=0)
    
    time = 0
    # plot_graph(properties, property_coordinates, time,folder_path)
    output.plot_map(properties, property_coordinates, time,xlims=xlims, ylims=ylims, save_folder = folder_path)
    plotting_list = []
    
    FOI = list(np.zeros(params['n']))
    plt.figure()
    # start time loop
    infected_properties = 1 # so the while loop begins
    while infected_properties > 0:
        time += 1

        controlzone= None

        if time >= params['policy_start']:
            # break/remove neighbour lines at radius r<= 'policy_r' around reported properties
            coordlist_of_infected_properties = []
            for i, premise in enumerate(properties):
                if premise.reported_status ==  True:
                    coordlist_of_infected_properties.append(premise.coordinates)

            if coordlist_of_infected_properties != []:

                controlzone = management.define_control_zone_circles(coordlist_of_infected_properties,params['policy_r'])

                for i, premise in enumerate(properties): 
                    if controlzone.contains(Point(premise.coordinates)):
                        old_neighbourhood = premise.neighbourhood
                        premise.neighbourhood = []
                        premise.total_neighbours = 0
                        # go through the old neighbours and remove their connection to this neighbour
                        for farm in old_neighbourhood[:]:
                            index = farm[0]
                            neighbour = properties[index]
                            neighbour_of_neighbour = neighbour.neighbourhood
                            for x in neighbour_of_neighbour[:]:
                                if x[0] == i:
                                    neighbour.neighbourhood.remove(x)
                                    break
                                

        plotting_list.append([])
        infected_properties = 0
        for i, premise in enumerate(properties):
            if not premise.culled_status:
                FOI[i] = SEIR.calculate_force_of_infection(properties, i, params)

        # run infection model for each property
        for i, premise in enumerate(properties): 
            # if the property has not been culled
            if not premise.culled_status:
                # run infection model and update infection numbers 
                premise.infection_model(params, FOI[i],time)
                cumulative_infection_proportions[i] = premise.cumulative_infections/premise.size

                # does the property vaccinate?
                # property can only vaccinate if they are not infected already
                if not premise.infection_status:
                    # calculate infected neighbours
                    if len(premise.neighbourhood): #premise has neighbours
                        neighbours = [el[0] for el in premise.neighbourhood]
                        culled_neighbours = sum([properties[i].culled_status for i in neighbours])
                        prop_culled_neighbours = culled_neighbours/premise.total_neighbours
                    else: #no neighbours
                        prop_culled_neighbours = 0


                    premise.vaccination(params, prop_culled_neighbours, time)
                 # does the property report?
                # property can only report if they are infected and have not been culled yet
                else:
                    infected_properties += 1 # counting infected properties while we're considering infected properties
                    premise.reporting(params,time)
            # if property has been culled
            else: 
                # keeping track of infected_proportions for all properties
                cumulative_infection_proportions[i] = 0
        
        if plotting:
            # plot_graph(properties, property_coordinates, time,folder_path)
            output.plot_map(properties, property_coordinates, time,xlims=xlims, ylims=ylims, save_folder =folder_path,real_situation=True,controlzone=controlzone)
            output.plot_map(properties, property_coordinates, time,xlims=xlims, ylims=ylims, save_folder =folder_path,real_situation=False,controlzone=controlzone)
            output.save_data(properties,property_coordinates, time,controlzone,folder_path,)


        
    
    if plotting:
        output.make_video(folder_path,"map_underlying")
        output.make_video(folder_path,"map_apparent")

    for premise in properties:
        if premise.culled_status:
            total_culled += 1
        if premise.vaccination_status:
            total_vaccinated += 1

    # print output
    header = ['id','status','ip','exposure_date','clinical_date','notification_date','removal_date','recovery_date','vacc_date','region','county','cluster','xcoord','ycoord','area','type','total']
    file =  os.path.join(folder_path,f"fake_data{unique_output}.csv")
    with open(file, 'w', newline='') as f:
        
        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_output_row()
            writer.writerow(row)

        
    return total_culled, total_vaccinated
