# Technical notes and references

### To update the FMD_modelling submodule, either:

Go into the directory and run `git fetch` and `git merge`

Or, run `git submodule update --remote FMD_modelling`


### To pull the repository:

`git pull`

`git submodule update --init --recursive`


### For Markdown syntax:

[Markdown Cheat Sheet](https://www.markdownguide.org/cheat-sheet/)


### To run testing

In commandline: 

`pytest` 


### Virtual environment

Initiate virtual environment using the following if not yet created

`python -m venv venv`

Then activate (on Windows) with

`. venv/Scripts/activate`

And then you should be in the virtual environment!

You can then deactivate with:

`deactivate`