# spaCy-wrapped DBpedia Spotlight Service

The NER (Named Entity Recognizer) and NEL (Named Entity Linking) tool wrapped as a CLAMS service, using [DBpedia Spotlight and spaCy](https://github.com/MartinoMensio/spacy-dbpedia-spotlight).

This requires Python 3.6 or higher. For local install of required Python modules do:

```bash
$ pip install clams-python==0.5.1
$ pip install spacy==3.3.1
```

In an earlier version of this application we had to manually install click==7.1.1 because clams-python installed version 8.0.1 and spaCy was not compatible with that version. The spacy install now does that automatically.

You also need the small spaCy model. Even if you have already download a model named `en_core_web_sm` with the older version of spaCy, it is important that you run the following command, because different versions of spaCy use the name `en_core_web_sm` to refer to slightly different models.

```bash
$ python -m spacy download en_core_web_sm
```

## Using this service

Use `python app.py -t example-mmif.json out.json` just to test the wrapping code without using a server. To test this using a server you run the app as a service in one terminal (when you add the optional  `--develop` parameter a Flask server will be used in development mode, otherwise you will get a production Gunicorn server):

```bash
$ python app.py [--develop]
```

And poke at it from another:

```bash
$ curl http://0.0.0.0:5000/
$ curl -H "Accept: application/json" -X POST -d@input-mmif/example-transcript.json http://0.0.0.0:5000/
```

In CLAMS you usually run this in a Docker container. To create a Docker image

```bash
$ docker build -t clams-dbpedia .
```

And to run it as a container:

```bash
$ docker run --rm -d -p 5000:5000 clams-dbpedia
$ curl -H "Accept: application/json" -X POST -d@input-mmif/example-transcript.json http://0.0.0.0:5000/
```

The spaCy code will run on each text document in the input MMIF file. The file `input-mmif/example-transcript.json` has one view, containing one text document. The text document looks as follows:

```json
{
  "@type": "http://mmif.clams.ai/0.4.0/vocabulary/TextDocument",
  "properties": {
   "text": {
      "@value": "Hello, this is Jim Lehrer with the NewsHour on PBS...."
    },
	  "id": "td1"
  }
}
```
Instead of a `text:@value` property the text could in an external file, which would be given as a URI in the `location` property. See the readme file in [https://github.com/clamsproject/app-nlp-example](https://github.com/clamsproject/app-nlp-example) on how to do this.

## Using this service with an uncased NER model

The DBpedia Spotlight NER (Named Entity Recognition) is optimized for cased input, but is not robust against lowercase input. For example, many person names, if in lowercase, would not be recognized and linked to their respective DBpedia pages. However, the recall could be significantly improved when these named entities are capitalized.

As a result, when running `app.py`, an option could be specified so that the app would scan the input mmif file for named entities (i.e. annotations of the 'NamedEntity' type) as recognized by a spaCy model (which, in practice, means the uncased NER model from [this repo](https://github.com/JinnyViboonlarp/app-spacy-nlp-ner#using-this-service-with-an-uncased-ner-model)), and then capitalize the corresponding instances of these named entities in the texts in the mmif file. This method is informally called the "truecasing trick" and is shown to improve the app's NER capacity when the input texts are in lowercase.

To test the app **without** the truecasing trick, run the below command on your terminal. This is recommended when the input text is **cased**.

```
$ python app.py -t input-mmif/example-transcript.json output-mmif/example-transcript.json
```

To test the app **with** the truecasing trick, use this command instead. This is recommended when the input text is **uncased**.

```
$ python app.py -t --truecase input-mmif-uncased/example-transcript.json output-mmif-uncased/example-transcript.json
```

## Testing the app in a Docker container

To test the app **without** the truecasing trick, run the below command on your terminal.
```
$ docker build -t clams-dbpedia-cased -f Dockerfile-cased .
$ docker run --rm -d -p 5000:5000 clams-dbpedia-cased
$ python annotate_all_transcripts.py
```

To test the app **with** the truecasing trick, use this command instead.
```
$ docker build -t clams-dbpedia-uncased -f Dockerfile-uncased .
$ docker run --rm -d -p 5000:5000 clams-dbpedia-uncased
$ python annotate_all_transcripts.py --uncased
```

