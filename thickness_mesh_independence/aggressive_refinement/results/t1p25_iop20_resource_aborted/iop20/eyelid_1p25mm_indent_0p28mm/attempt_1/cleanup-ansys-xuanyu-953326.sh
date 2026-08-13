LOCALHOST=`hostname -s`
if [ $LOCALHOST = xuanyu ]; then kill -9 953327; else ssh xuanyu kill -9 953327; fi
if [ $LOCALHOST = xuanyu ]; then kill -9 953328; else ssh xuanyu kill -9 953328; fi
if [ $LOCALHOST = xuanyu ]; then kill -9 953325; else ssh xuanyu kill -9 953325; fi
if [ $LOCALHOST = xuanyu ]; then kill -9 953326; else ssh xuanyu kill -9 953326; fi

rm -f cleanup-ansys-xuanyu-953326.sh
