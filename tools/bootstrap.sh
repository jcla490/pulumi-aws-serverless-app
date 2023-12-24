#!/bin/bash
[ ! -z $DEBUG ] && set -x

SUCCESS_COLOR='\033[0;32m'
WARN_COLOR='\033[1;33m'

PYTHON_VER=3.10.7
PROJECT_NAME=pulumi-aws-bootstrap

CWD=$(pwd)
cd $(dirname $0)/..
cd $CWD

echo "-----------------------------------------------"
echo "Bootstrapping python $PYTHON_VER environment..."

installed_version=$(pyenv versions | grep "$PYTHON_VER")
case "$installed_version" in 
  *$PYTHON_VER*)
    echo "Python version $PYTHON_VER is already installed"
    ;;
*)
  echo "Python version $PYTHON_VER is not installed - installing now..."
  pyenv install $PYTHON_VER

  [ $? -ne 0 ] && echo -e "${WARN_COLOR}ERROR: Unable to install required python version" && exit 1
  ;;
esac

pyenv virtualenv $PYTHON_VER $PROJECT_NAME
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv local $PROJECT_NAME
pyenv activate $PROJECT_NAME 

echo "-----------------------------------------------"
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "-----------------------------------------------"
echo "Installing pulumi CLI..."
brew install pulumi/tap/pulumi

echo "-----------------------------------------------"
echo -e "${SUCCESS_COLOR}🚀  Look at you go, everything installed successfully!"
