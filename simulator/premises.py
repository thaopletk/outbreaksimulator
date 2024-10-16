import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))
sys.path.append(os.path.join(os.path.dirname(__file__),"..","FMD_modelling"))
from class_definitions import Property, Animal 
import datetime
import itertools


def convert_time_to_date(time,start_date=datetime.datetime(year=2024, month=11, day=1)):
    current_date = start_date+ datetime.timedelta(days=time)
    return current_date.strftime("%d/%m/%Y")

# for now, we need additional parameters, hence inheriting from the fmdmodelling code
class Premises(Property):
    id_iter = itertools.count()
    notified_iter = itertools.count()
    
    def __init__(self, params):
        super().__init__(params) 

        self.area = 500 # some random number, overriding the default 0, unknown units (should probably be converted properly)

        self.reported_status = False

        # things required for output, for input into the downstream model
        self.id = next(Premises.id_iter)
        self.status = "NA"
        self.ip = "NA"
        self.exposure_date = "NA"
        self.clinical_date= "NA"
        self.notification_date = "NA"
        self.removal_date = "NA"
        self.recovery_date = "NA"
        self.vacc_date = "NA"
        self.region = "NA"
        self.county="NA"
        self.cluster= "NA"
        self.type = "NA"

    def vaccination(self, params, properties,time):
        super().vaccination( params, properties)
        if self.vaccination_status == 1:
            self.vacc_date = convert_time_to_date(time)

        return 

    def reporting(self, params,time):
        super().reporting(params)
        if self.culled_status==1:
            self.notification_date = convert_time_to_date(time)
            self.status = "IP"
            self.ip = next(Premises.notified_iter)
            self.reported_status = True
        return 

    def infection_model(self, params, FOI,time):
        super().infection_model(params,FOI)

        if self.infection_status==1 and self.clinical_date == "NA":
            self.clinical_date = convert_time_to_date(time) # might need to change this, but for now, it should be the earliest date with clinical symptoms

    def return_output_row(self):
        # id	status	ip	exposure_date	clinical_date	notification_date	removal_date	recovery_date	vacc_date	region	county	cluster	xcoord	ycoord	area	type	total

        return [self.id, self.status, self.ip, self.exposure_date, self.clinical_date, self.notification_date, self.removal_date, self.recovery_date, self.vacc_date, self.region, self.county, self.cluster, self.coordinates[0], self.coordinates[1],self.area,self.type, self.size]