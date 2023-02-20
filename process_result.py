import os
import json
from datetime import datetime, timedelta
from typing import NamedTuple
import argparse
import pandas as pd
from datetime import datetime, timezone
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError

global credential
global client
global workspace_id
credential = DefaultAzureCredential()
client = LogsQueryClient(credential)
workspace_id=os.environ['LOG_WORKSPACE_ID']

class RunInfo(NamedTuple):
    engine_name: str
    setup_name: str
    dataset_name: str
    # operation_type: str
    # run_num: int
    
class SearchResultInfo(NamedTuple):
    total_time: float
    mean_time: float
    mean_precisions: float
    rps: float
    p95_time: float
    p99_time: float
    parallel: float
    start_timestamp: str
    end_timestamp: str
    engine_params: tuple

class UploadResultInfo(NamedTuple):
    dataset_size: int
    upload_time: float
    total_upload_time: float
    start_timestamp: str
    end_upload_timestamp: str
    end_load_timestamp: str
    avg_node_memory_gb: float
    avg_node_cpu_cores: float

def parse_file_name(file_name):
    parts = file_name.split("-")
    m_idx = parts.index("m")
    try:
        op_idx = parts.index("search")
    except:
        try:
            op_idx = parts.index("upload")
        except:
            return None
    s = "-"
    
    operation_type = f"{parts[op_idx]}"
    engine_name = f"{parts[0]}"
    setup_name = f"{engine_name}-{s.join(parts[m_idx:m_idx + 4])}"
    
    dataset_name = s.join(parts[m_idx + 4:op_idx])
    # run_num = parts[op_idx+1]
    return RunInfo(engine_name, setup_name, dataset_name)

def parse_search_file_content(file_content):
    total_time = file_content["results"]["total_time"]
    mean_time = file_content["results"]["mean_time"]
    mean_precisions = file_content["results"]["mean_precisions"]
    rps = file_content["results"]["rps"]
    p95_time = file_content["results"]["p95_time"]
    p99_time = file_content["results"]["p99_time"]
    parallel = file_content["params"]["parallel"]
    start_timestamp = file_content["results"]["start_timestamp"]
    end_timestamp = file_content["results"]["end_timestamp"]
    # print(file_content["params"])
    engine_params = list(file_content["params"].items())[1]
    # print(type(engine_params))
    return SearchResultInfo(total_time, mean_time, mean_precisions, rps, p95_time, p99_time, parallel, start_timestamp, end_timestamp, engine_params)

def parse_upload_file_content(file_content):
    upload_time = file_content["results"]["upload_time"]
    total_upload_time = file_content["results"]["total_time"]
    dataset_size = file_content["results"]["dataset_size"]
    start_timestamp = file_content["results"]["start_timestamp"]
    end_upload_timestamp = file_content["results"]["end_upload_timestamp"]
    end_load_timestamp = file_content["results"]["end_load_timestamp"]
    return UploadResultInfo(dataset_size, upload_time, total_upload_time, start_timestamp, end_upload_timestamp, end_load_timestamp, 0, 0)

def get_avg_cpu_cores(engine_name, start_str_time, end_str_time):
    start_time=datetime.fromisoformat(start_str_time)
    end_time=datetime.fromisoformat(end_str_time)
    start_time = start_time.replace(second=0, microsecond=0)
    end_time = end_time + timedelta(minutes=1)
    end_time = end_time.replace(second=0, microsecond=0)
    start_str_time = start_time.isoformat()
    end_str_time = end_time.isoformat()
            
    target_column_name="AvgNodeCPUUsageCores"

    queryNodeCPUUsage = f"""
let endDateTime = datetime('{end_str_time}');
let startDateTime = datetime('{start_str_time}');
let trendBinSize = 1m;
let capacityCounterName = 'cpuCapacityNanoCores';
let usageCounterName = 'cpuUsageNanoCores';
KubeNodeInventory
| where TimeGenerated < endDateTime
| where TimeGenerated >= startDateTime
// cluster filter would go here if multiple clusters are reporting to the same Log Analytics workspace
| where ClusterName contains '{engine_name}'
| distinct ClusterName, Computer, _ResourceId
| join hint.strategy=shuffle (
  Perf
  | where TimeGenerated < endDateTime
  | where TimeGenerated >= startDateTime
  | where ObjectName == 'K8SNode'
  | where CounterName == capacityCounterName
  | summarize LimitValue = max(CounterValue) by Computer, CounterName, bin(TimeGenerated, trendBinSize)
  | project Computer, CapacityStartTime = TimeGenerated, CapacityEndTime = TimeGenerated + trendBinSize, LimitValue
) on Computer
| join kind=inner hint.strategy=shuffle (
  Perf
  | where TimeGenerated < endDateTime + trendBinSize
  | where TimeGenerated >= startDateTime - trendBinSize
  | where ObjectName == 'K8SNode'
  | where CounterName == usageCounterName
  | project Computer, UsageValue = CounterValue, TimeGenerated
) on Computer
| where TimeGenerated >= CapacityStartTime and TimeGenerated < CapacityEndTime
| project ClusterName, Computer, TimeGenerated, UsageValue, LimitValue, UsagePercent = UsageValue * 100.0 / LimitValue, _ResourceId
| summarize {target_column_name} = avg(UsageValue)/1000000000 by bin(TimeGenerated, trendBinSize), ClusterName
"""
    try:
        response = client.query_workspace(
            workspace_id=workspace_id,
            query=queryNodeCPUUsage,
            timespan=(start_time, end_time)
        )
        if response.status == LogsQueryStatus.PARTIAL:
            error = response.partial_error
            data = response.partial_data
            print(error)
        elif response.status == LogsQueryStatus.SUCCESS:
            data = response.tables
        for table in data:
            df = pd.DataFrame(data=table.rows, columns=table.columns)
    except HttpResponseError as err:
        print("something fatal happened")
        print(err)
    result = df[target_column_name].mean()
    # print(target_column_name, result)
    return result

def get_avg_memory_gb(engine_name, start_str_time, end_str_time):
    start_time=datetime.fromisoformat(start_str_time)
    end_time=datetime.fromisoformat(end_str_time)
    start_time = start_time.replace(second=0, microsecond=0)
    end_time = end_time + timedelta(minutes=1)
    end_time = end_time.replace(second=0, microsecond=0)
    start_str_time = start_time.isoformat()
    end_str_time = end_time.isoformat()
            
    target_column_name="AvgNodeMemoryUsage_GB"

    queryNodeMemoryUsage = f"""
let startDateTime = datetime('{start_str_time}');
let endDateTime = datetime('{end_str_time}');
let trendBinSize = 1m;
let capacityCounterName = 'memoryCapacityBytes';
let usageCounterName = 'memoryRssBytes';
KubeNodeInventory
| where TimeGenerated < endDateTime
| where TimeGenerated >= startDateTime
// cluster filter would go here if multiple clusters are reporting to the same Log Analytics workspace
| where ClusterName contains '{engine_name}'
| distinct ClusterName, Computer, _ResourceId
| join hint.strategy=shuffle (
  Perf
  | where TimeGenerated < endDateTime
  | where TimeGenerated >= startDateTime
  | where ObjectName == 'K8SNode'
  | where CounterName == capacityCounterName
  | summarize LimitValue = max(CounterValue) by Computer, CounterName, bin(TimeGenerated, trendBinSize)
  | project Computer, CapacityStartTime = TimeGenerated, CapacityEndTime = TimeGenerated + trendBinSize, LimitValue
) on Computer
| join kind=inner hint.strategy=shuffle (
  Perf
  | where TimeGenerated < endDateTime + trendBinSize
  | where TimeGenerated >= startDateTime - trendBinSize
  | where ObjectName == 'K8SNode'
  | where CounterName == usageCounterName
  | project Computer, UsageValue = CounterValue, TimeGenerated
) on Computer
| where TimeGenerated >= CapacityStartTime and TimeGenerated < CapacityEndTime
| project ClusterName, Computer, TimeGenerated, UsageValue, LimitValue, UsagePercent = UsageValue * 100.0 / LimitValue, _ResourceId
| summarize {target_column_name} = avg(UsageValue)/1024/1024/1024 by bin(TimeGenerated, trendBinSize), ClusterName
"""
    try:
        response = client.query_workspace(
            workspace_id=workspace_id,
            query=queryNodeMemoryUsage,
            timespan=(start_time, end_time)
        )
        if response.status == LogsQueryStatus.PARTIAL:
            error = response.partial_error
            data = response.partial_data
            print(error)
        elif response.status == LogsQueryStatus.SUCCESS:
            data = response.tables
        for table in data:
            df = pd.DataFrame(data=table.rows, columns=table.columns)
    except HttpResponseError as err:
        print("something fatal happened")
        print(err)
    result = df[target_column_name].mean()
    # print(target_column_name, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", help="result path", default="results")
    parser.add_argument("--output-path", help="output path", default="website")
    parser.add_argument("--output-file", help="output file name", default="results.json")
    args = parser.parse_args()
    print(args)
    input_path = args.input_path
    output_path = args.output_path
    output_file = args.output_file

    print("Input path:", input_path)
    print("Output path:", output_path)
    print("Output file:", output_file)
    print("workspace_id:", workspace_id)
    
    results_path = os.path.join(output_path, output_file)
    result = []
    run_upload_map = {}
    run_search_map = {}
    if os.path.exists(results_path):
        print(results_path, "found")
        result_file = open(results_path, 'r')
        result = json.load(result_file)
        for result_info in result:
            engine_name = result_info["engine_name"]
            setup_name = result_info["setup_name"]
            dataset_name = result_info["dataset_name"]

            upload_time = result_info["upload_time"]
            total_upload_time = result_info["total_upload_time"]
            dataset_size = result_info["dataset_size"]
            avg_node_memory_gb = result_info["upload_avg_node_memory_gb"]
            avg_node_cpu_cores = result_info["upload_avg_node_cpu_cores"]

            rps = result_info["rps"]
            parallel = result_info["parallel"]
            p95_time = result_info["p95_time"]
            p99_time = result_info["p99_time"]
            mean_time = result_info["mean_time"]
            mean_precisions = result_info["mean_precisions"]
            engine_params = result_info["engine_params"]

            run_info = RunInfo(engine_name, setup_name, dataset_name)
            upload_info = UploadResultInfo(
                            dataset_size, 
                            upload_time, 
                            total_upload_time, 
                            "start_timestamp", 
                            "end_upload_timestamp", 
                            "end_load_timestamp", 
                            avg_node_memory_gb, 
                            avg_node_cpu_cores)
            search_info = SearchResultInfo(
                            0, #total_time, 
                            mean_time, 
                            mean_precisions, 
                            rps, 
                            p95_time, 
                            p99_time, 
                            parallel, 
                            "start_timestamp", 
                            "end_timestamp",
                            None #engine_params
                        )

            if not run_upload_map.get(run_info):
                run_upload_map[run_info] = upload_info
                #print("Add:", upload_info)

            if not run_search_map.get(search_info):
                run_search_map[search_info] = upload_info
                #print("Add:", search_info)

    for file_name in os.listdir(input_path):
        if file_name.endswith(".json") and file_name.find('upload') != -1:
            file_path = os.path.join(input_path, file_name)
            with open(file_path, 'r') as f:
                file_content = json.load(f)
            run_info = parse_file_name(file_name)
            
            # check upload info
            if run_upload_map.get(run_info):
                print("\nSkip upload info processing:",run_info, run_upload_map.get(run_info))
                continue
            upload_info = parse_upload_file_content(file_content)
            
            # get cluster info
            start_str_time = upload_info.start_timestamp
            end_str_time = upload_info.end_load_timestamp
            engine_name = run_info.engine_name
            
            avg_node_memory_gb = get_avg_memory_gb(engine_name, start_str_time, end_str_time)
            avg_node_cpu_cores = get_avg_cpu_cores(engine_name, start_str_time, end_str_time)

            upload_info = upload_info._replace(avg_node_memory_gb=avg_node_memory_gb, avg_node_cpu_cores=avg_node_cpu_cores)
            print(upload_info, "\n")
            run_upload_map[run_info] = upload_info
            
    for file_name in os.listdir(input_path):
        if file_name.endswith(".json") and file_name.find('search') != -1:
            file_path = os.path.join(input_path, file_name)
            with open(file_path, 'r') as f:
                file_content = json.load(f)
            run_info = parse_file_name(file_name)
            try:
                search_info = parse_search_file_content(file_content)
            except Exception as e:
                print(f"Parsing error, skip this file:{file_name}")
                continue

            # check search info
            search_key_info = search_info._replace(total_time = 0, start_timestamp = "start_timestamp", end_timestamp = "end_timestamp", engine_params = None)
            if run_search_map.get(search_key_info):
                print("\nSkip search info processing:", run_info, search_info)
                continue

            upload_info = run_upload_map[run_info]
            
            start_str_time = search_info.start_timestamp
            end_str_time = search_info.end_timestamp
            engine_name = run_info.engine_name
            
            avg_node_memory_gb = get_avg_memory_gb(engine_name, start_str_time, end_str_time)
            avg_node_cpu_cores = get_avg_cpu_cores(engine_name, start_str_time, end_str_time)
            
            result_info = {
                'engine_name': run_info.engine_name,
                'setup_name': run_info.setup_name,
                'dataset_name': run_info.dataset_name,
                'dataset_size': upload_info.dataset_size,
                'upload_time': upload_info.upload_time,
                'total_upload_time': upload_info.total_upload_time,
                'upload_avg_node_memory_gb': upload_info.avg_node_memory_gb,
                'upload_avg_node_cpu_cores': upload_info.avg_node_cpu_cores,
                'p95_time': search_info.p95_time,
                'rps': search_info.rps,
                'parallel': search_info.parallel,
                'search_avg_node_memory_gb': avg_node_memory_gb,
                'search_avg_node_cpu_cores': avg_node_cpu_cores,
                'p99_time': search_info.p99_time,
                'mean_time': search_info.mean_time,
                'mean_precisions': search_info.mean_precisions,
                'engine_params': search_info.engine_params
            }
            print(result_info, "\n")
            result.append(result_info)

    jsonResult = json.dumps(result, indent=4)

    output = open(os.path.join(output_path, output_file), 'w')
    output.write(jsonResult)
    output.close()
    
if __name__ == "__main__":
    main()
    
    
 

