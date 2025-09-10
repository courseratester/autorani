#!/bin/bash

url="https://www.example.com"
python -m autorani.main explore url; 
python -m autorani.main generate url; 
python -m autorani.main run;