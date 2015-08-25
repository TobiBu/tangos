DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
export PYTHONPATH=$DIR/modules/:$PYTHONPATH
export PATH=$DIR/tools/:$PATH
export HALODB_ROOT=$DIR/../db_galaxies/

if [ -z "$HALODB_DEFAULT_DB" ]; then
    export HALODB_DEFAULT_DB=$DIR/data.db
fi

if [[ -e enivornment_local.sh ]]
then
    source environment_local.sh
fi
