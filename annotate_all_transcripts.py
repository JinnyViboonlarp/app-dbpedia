import os
import sys
import argparse

def annotate_input_mmif_files_without_docker(uncased_choice = False):
    # this module is used to test the clams app on all transcripts, without Docker  
    if(uncased_choice):
        in_dir = 'input-mmif-uncased'
        out_dir = 'output-mmif-uncased'
    else:
        in_dir = 'input-mmif'
        out_dir = 'output-mmif'
    for mmif_name in os.listdir(in_dir):
        if(mmif_name.endswith(".json")):
            in_path = in_dir + '/' + mmif_name
            out_path = out_dir + '/' + mmif_name
            if(uncased_choice):
                os.system("python app.py -t --truecase "+in_path+" "+out_path)
            else:
                os.system("python app.py -t "+in_path+" "+out_path)

def annotate_input_mmif_files(uncased_choice = False):
    # this module is used to test the clams app on all transcripts, with Docker
    # the docker container must first be running
    # The commands are "docker build -t clams-dbpedia -f Dockerfile-cased ." (or Dockerfile-uncased if truecase option) \
    # and then "docker run --rm -d -p 5000:5000 clams-dbpedia"
    if(uncased_choice):
        in_dir = 'input-mmif-uncased'
        out_dir = 'output-mmif-uncased'
    else:
        in_dir = 'input-mmif'
        out_dir = 'output-mmif'  
    for mmif_name in os.listdir(in_dir):
        if(mmif_name.endswith(".json")):
            in_path = in_dir + '/' + mmif_name
            out_path = out_dir + '/' + mmif_name
            os.system('curl -H "Accept: application/json" -X POST -d@' + in_path + ' http://0.0.0.0:5000/?pretty=True -o ' + out_path)

if __name__ == "__main__":

    #annotate_input_mmif_files_without_docker()

    parser = argparse.ArgumentParser()
    parser.add_argument('--uncased',  action='store_true', help="capitalize the already-recognized named entities")
    args = parser.parse_args()

    if args.uncased:
        uncased_choice = True
    else:
        uncased_choice = False
        
    annotate_input_mmif_files(uncased_choice)
