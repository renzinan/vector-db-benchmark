import os
import json
from datetime import datetime
from typing import NamedTuple
import argparse

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
    engine_params: tuple

class UploadResultInfo(NamedTuple):
    upload_time: float
    total_upload_time: float

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
    setup_name = f"{engine_name}-{s.join(parts[m_idx-1:m_idx + 4])}"
    
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
    # print(file_content["params"])
    engine_params = list(file_content["params"].items())[1]
    # print(type(engine_params))
    return SearchResultInfo(total_time, mean_time, mean_precisions, rps, p95_time, p99_time, parallel, engine_params)

def parse_upload_file_content(file_content):
    upload_time = file_content["results"]["upload_time"]
    total_upload_time = file_content["results"]["total_time"]
    return UploadResultInfo(upload_time, total_upload_time)

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
    
    run_map = {}
    result = []
    for file_name in os.listdir(input_path):
        if file_name.endswith(".json") and file_name.find('upload') != -1:
            file_path = os.path.join(input_path, file_name)
            with open(file_path, 'r') as f:
                file_content = json.load(f)
            run_info = parse_file_name(file_name)
            upload_info = parse_upload_file_content(file_content)
            run_map[run_info] = upload_info
    print(run_map)
            
    for file_name in os.listdir(input_path):
        if file_name.endswith(".json") and file_name.find('search') != -1:
            file_path = os.path.join(input_path, file_name)
            with open(file_path, 'r') as f:
                file_content = json.load(f)
            run_info = parse_file_name(file_name)
            search_info = parse_search_file_content(file_content)
            upload_info = run_map[run_info]
            result_info = {
                'engine_name': run_info.engine_name,
                'setup_name': run_info.setup_name,
                'dataset_name': run_info.dataset_name,
                'upload_time': upload_info.upload_time,
                'total_upload_time': upload_info.total_upload_time,
                'p95_time': search_info.p95_time,
                'rps': search_info.rps,
                'parallel': search_info.parallel,
                'p99_time': search_info.p99_time,
                'mean_time': search_info.mean_time,
                'mean_precisions': search_info.mean_precisions,
                'engine_params': search_info.engine_params
            }
            result.append(result_info)

    jsonResult = json.dumps(result, indent=4)

    output = open(os.path.join(output_path, output_file), 'w')
    output.write(jsonResult)
    output.close()
    
if __name__ == "__main__":
    main()
    
    
 

