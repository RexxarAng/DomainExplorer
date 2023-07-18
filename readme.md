# DomainExplorer

## Table of contents
* [Project Description](#Project-Decription)
* [Setup](#Setup)
* [Technologies](#Technologies)

## Project Description
The DomainExplorer is a web crawling application designed to discover and analyze the sequence of URLs within a website. Its primary purpose is to assist in testing and verification of URL management in web applications. By navigating through the website and capturing the sequence of URLs visited, the Spider Tool helps ensure that the expected URL flows and transitions are properly managed.

## Setup

* Install Python3 from the official website: 
  * https://www.python.org/downloads/
* Install google chrome: 
  * https://www.google.com/chrome
* Update the config.json file
  * start_urls with the urls to crawl
  * chrome_path with the path to the chrome executable
* Install python dependencies
  * ``pip install -r requirements.txt ``  


## Technologies
Project is created with:
* Pyppeteer
