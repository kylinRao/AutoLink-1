NAME='AutoLink'
echo $NAME
PID=`ps -ef | grep "$NAME" | grep python | grep -v grep | awk '{print $2}'`
echo "当前进程号为：$PID"
echo "---------------"
for pid in $PID
do
sleep 2
kill -9  $pid
echo "killed [$pid]"
done
nohup python AutoLink.py runserver -h 0.0.0.0 &
