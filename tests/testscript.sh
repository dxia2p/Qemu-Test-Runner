uname -a

if [ $? = 0 ]; then
    exit 0
else
    exit 1
fi
