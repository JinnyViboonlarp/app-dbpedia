# app-dbpedia

### Usage

testing mmif input file with cased texts

```
$ python app.py -t example-mmif.json out.json
```

testing mmif input file with uncased texts (with the semi-truecase option)

```
$ python app.py -t --truecase example-mmif-uncased.json out-uncased.json
```

### Test with docker

cased
- if there is container running at port 5000, stop it.
- change the last line of annotate_all_transcripts.py to `annotate_input_mmif_files(uncased_choice = False)`
```
$ docker build -t clams-dbpedia-cased -f Dockerfile-cased .
$ docker run --rm -d -p 5000:5000 clams-dbpedia-cased
$ python annotate_all_transcripts.py
```

uncased (i.e. using truecasing trick on the uncased data)
- if there is container running at port 5000, stop it.
- change the last line of annotate_all_transcripts.py to `annotate_input_mmif_files(uncased_choice = True)`
```
$ docker build -t clams-dbpedia-uncased -f Dockerfile-uncased .
$ docker run --rm -d -p 5000:5000 clams-dbpedia-uncased
$ python annotate_all_transcripts.py
```

