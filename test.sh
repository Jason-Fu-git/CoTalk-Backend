coverage run --source CoTalkBackend,user,chat,message,ws,utils -m pytest --junit-xml=xunit-reports/xunit-result.xml
ret=$?
coverage xml -o coverage-reports/coverage.xml
coverage report
exit $ret