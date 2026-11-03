// Read only one explicitly named task; never registers, changes or starts a task.
var service = new ActiveXObject("Schedule.Service");
service.Connect();
var task = service.GetFolder("\\").GetTask(WScript.Arguments(0));
WScript.Echo('{"run_level":'+task.Definition.Principal.RunLevel+
             ',"state":'+task.State+',"last_result":'+task.LastTaskResult+
             ',"enabled":'+(task.Enabled?'true':'false')+'}');
