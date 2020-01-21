# -*- coding: utf-8 -*-
"""
Created on December 16, 2019
Version 2.3 

Copyright (c) 2019 Thomas Beha

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    https://www.gnu.org/licenses/gpl-3.0.en.html 

"""

from cryptography.fernet import *
from lxml import etree 
import time
from SimpliVityClass import *
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server

BtoGB=pow(1024,3)
BtoMB=pow(1024,2)
#path = './'
path = '/opt/svt/data'
 

node_state={
    'UNKOWN': 0,
    'ALIVE': 1,
    'SUSPECTED': 2,
    'MANAGED': 3,
    'FAULTY': 4,
    'REMOVED': 5
}

vm_state={
    'ALIVE': 1,
    'DELETED': 2,
    'REMOVED': 3
}

capacitymetric=[
    'allocated_capacity',
    'free_space',
    'capacity_savings',
    'used_capacity',
    'used_logical_capacity',
    'local_backup_capacity',
    'remote_backup_capacity',
    'stored_compressed_data',
    'stored_uncompressed_data',
    'stored_virtual_machine_data'
]

dedupmetric=[
    'compression_ratio',
    'deduplication_ratio',
    'efficiency_ratio'
]

performancemetric=[
    'read_iops',
    'write_iops',
    'read_throughput',
    'write_throughput',
    'read_latency',
    'write_latency'
]

def logwriter(f, text):
        output=str(datetime.today()) +": "+text+" \n"
        print(output)
        f.write(output)
    
def logopen(filename):
        f = open(filename,'a')
        f.write(str(datetime.today())+": Logfile opened \n")
        return f

def logclose(f):
        f.write(str(datetime.today())+": Logfile closed \n")
        f.close()

def getPerformanceAverage(data):
        perf={
            'read_iops': 0,
            'write_iops': 0,
            'read_throughput': 0,
            'write_throughput': 0,
            'read_latency': 0,
            'write_latency': 0
        }
        for x in data:
            if x['name'] == 'iops':
                i=0
                for y in x['data_points']:
                    perf['read_iops'] += y['reads']
                    perf['write_iops'] += y['writes']
                    i += 1
                if i > 0:   
                    perf['read_iops'] /= i 
                    perf['write_iops'] /= i
                else:
                    perf['read_iops'] = -1 
                    perf['write_iops'] = -1                    
            if x['name'] == 'throughput':
                i=0
                for y in x['data_points']:
                    perf['read_throughput'] += y['reads']
                    perf['write_throughput'] += y['writes']
                    i += 1
                if i > 0:
                    perf['read_throughput'] /= (i * BtoMB)
                    perf['write_throughput'] /= (i * BtoMB)
                else:
                    perf['read_throughput'] = -1
                    perf['write_throghput'] = -1 
            if x['name'] == 'latency':
                i=0
                for y in x['data_points']:
                    perf['read_latency'] += y['reads']
                    perf['write_latency'] += y['writes']
                    i += 1
                if i > 0:
                    perf['read_latency'] /= (i * 1000) 
                    perf['write_latency'] /= (i * 1000)
                else:
                    perf['read_latency'] = -1 
                    perf['write_latency'] = -1                
        return(perf)

def getNodeCapacity(data):
        ndata={
            'allocated_capacity': 0,
            'free_space': 0,
            'capacity_savings': 0,
            'used_capacity': 0,
            'used_logical_capacity': 0,
            'local_backup_capacity': 0,
            'remote_backup_capacity': 0,
            'stored_compressed_data': 0,
            'stored_uncompressed_data': 0,
            'stored_virtual_machine_data': 0,
            'compression_ratio': 0,
            'deduplication_ratio': 0,
            'efficiency_ratio': 0                              
        }
        for y in data:
            if 'ratio' in y['name']:
                ndata[y['name']]=y['data_points'][-1]['value']
            else: 
                ndata[y['name']] = y['data_points'][-1]['value']/BtoGB
        return ndata

### Main ###########################################################################

if __name__ == "__main__":
    
    t0=time.time()
    """ read the key and input file """
    keyfile= path + 'SvtConnector.key'
    xmlfile=path + 'SvtConnector.xml'

    """ Parse XML File """
    tree = etree.parse(xmlfile)
    u2=(tree.find("user")).text
    p2=(tree.find("password")).text
    ovc=(tree.find("ovc")).text
    mintervall=int((tree.find("monitoringintervall")).text)
    mresolution=(tree.find("resolution")).text
    mrange=(tree.find("timerange")).text
    lfile=(tree.find("logfile")).text
    port=int((tree.find("port")).text)

    """ Open the logfile """ 
    log=logopen(path+lfile)

    """ Read keyfile """
    f = open(keyfile, 'r')
    k2=f.readline()
    f.close()
    key2=k2.encode('ASCII')
    f = Fernet(key2)

    """ Create the SimpliVity Rest API Object"""
    logwriter(log,"Open a connection to the SimpliVity systems")
    svtuser = f.decrypt(u2.encode('ASCII')).decode('ASCII')
    svtpassword = f.decrypt(p2.encode('ASCII')).decode('ASCII')
    url="https://"+ovc+"/api/"         
    svt = SimpliVity(url)
    logwriter(log,"Open Connection to SimpliVity")
    svt.Connect(svtuser,svtpassword)
    logwriter(log,"Connection to SimpliVity is open")
    logclose(log)
        
    start_http_server(port)
    c = Counter('simplivity_sample','SimpliVity sample number')
    scluster = Gauge('simplivity_cluster','SimpliVity Cluster Data',['clustername','clustermetric'])
    snode = Gauge('simplivity_node','SimpliVity Node Data',['nodename','nodemetric'])
    svm = Gauge('simplivity_vm','SimpliVity VM Data',['vmname','vmmetric'])
    sdatastore = Gauge('simplivity_datastore','SimpliVity Datastore Data - Sizes in GB',['dsname','dsmetric'])
    delta = Gauge('ConnectorRuntime','Time required for last data collection in seconds')

    """
    Start an endless loop to capture the current status every TIME_RANGE
    Errors will be catched with an error routine
    Please note that the connection must be refreshed after 24h or afte 10 minutes inactivity.
    """

    while True:                
        try:
            t0 = time.time()         
            c.inc()
            clusters = svt.GetCluster()['omnistack_clusters']
            hosts = svt.GetHost()['hosts']
            vms = svt.GetVM()['virtual_machines']
            datastores = svt.GetDataStore()['datastores']
            scluster.labels('Federation','Cluster_count').set(len(clusters))
            snode.labels('Federation','Node_count').set(len(hosts))
            svm.labels('Federation','VM_count').set(len(vms))
            sdatastore.labels('Federation','Datastore_count').set(len(datastores))
            """  Cluster metrics: """
            for x in clusters:        
                perf=getPerformanceAverage(svt.GetClusterMetric(x['name'],timerange=mrange,resolution=mresolution)['metrics'])
                cn = (x['name'].split('.')[0]).replace('-','_')
                for metricname in capacitymetric:
                    scluster.labels(cn,metricname).set(x[metricname]/BtoGB)
                for metricname in dedupmetric:
                    scluster.labels(cn,metricname).set(x[metricname].split()[0])
                for metricname in performancemetric:
                    scluster.labels(cn,metricname).set(perf[metricname])
                for x in svt.GetClusterThroughput():
                    cn = x['source_omnistack_cluster_name']
                    metricname=x['destination_omnistack_cluster_name']+' throughput'
                    scluster.labels(cn,metricname).set(x['throughput'])

            """  Node metrics: """
            for x in hosts:
                y = getNodeCapacity(svt.GetHostCapacity(x['name'],timerange=mrange,resolution=mresolution)['metrics'])
                perf=getPerformanceAverage(svt.GetHostMetrics(x['name'],timerange=mrange,resolution=mresolution)['metrics'])
                cn = (x['name'].split('.')[0]).replace('-','_')
                snode.labels(cn,'State').set(node_state[x['state']])
                for metricname in capacitymetric:
                    snode.labels(cn,metricname).set(y[metricname])
                for metricname in dedupmetric:
                    snode.labels(cn,metricname).set(y[metricname])
                for metricname in performancemetric:
                    snode.labels(cn,metricname).set(perf[metricname])
                        
            """  VM metrics: """
            for x in vms:
                cn = (x['name'].split('.')[0]).replace('-','_')
                svm.labels(cn,'state').set(vm_state[x['state']]) 
                """                           
                perf=getPerformanceAverage(svt.GetVMMetric(x['name'],timerange=mrange,resolution=mresolution)['metrics'])
                for metricname in performancemetric:
                    svm.labels(cn,metricname).set(perf[metricname])                           
                """

            """ DataStore metrics """
            for x in datastores:
                cn = (x['name']).replace('-','_')
                sdatastore.labels(cn,'size').set(x['size']/BtoGB)
                        
            t1 = time.time()
            delta.set((t1-t0))
            while ((t1-t0) < mintervall):
                time.sleep(1.0)
                t1 = time.time()  
        except KeyError:
            log=logopen(path+lfile)
            logwriter(log,"KeyError")
            logwriter(log,str(e.expression))
            logwriter(log,str(e.status))
            logwriter(log,str(e.message))
            logclose(log)                         
        except SvtError as e:
            if e.status == 401:
                try:
                    log=logopen(path+lfile)
                    logwriter(log,"Open Connection to SimpliVity")
                    svt.Connect(svtuser,svtpassword)
                    logwriter(log,"Connection to SimpliVity is open")
                    logclose(log)
                except SvtError as e:
                    log=logopen(path+lfile)
                    logwriter(log,"Failed to open a conection to SimplVity")
                    logwriter(log,str(e.expression))
                    logwriter(log,str(e.status))
                    logwriter(log,str(e.message))
                    logwriter(log,"close SimpliVity connection")
                    logclose(log)
                    exit(-200)
            elif e.status == 555:
                log=logopen(path+lfile)
                logwriter(log,'SvtError:')
                logwriter(log,str(e.expression))
                logwriter(log,str(e.status))
                logwriter(log,str(e.message))
                logclose(log)                            
            else:
                log=logopen(path+lfile)
                logwriter(log,'Unhandeled SvtError:')
                logwriter(log,str(e.expression))
                logwriter(log,str(e.status))
                logwriter(log,str(e.message))
                logwriter(log,"close SimpliVity connection")
                logclose(log)
                exit(-200)        
