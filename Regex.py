

**regex_title**
```
r'^(?P<title>.*)$'
```
**regex**
```
r'S(?P<season>\d+)E(?P<episode>\d+)'
```
**regex_ep**
```
r'E(?P<episode>\d{1,4})(?=$|[^a-zA-Z])'
```
**regex_ep_range**
```
r'E(?P<episode_start>\d{1,4})-(?P<episode_end>\d{1,4})(?=$|[^a-zA-Z])'
```
**regex_season**
```
r'S(?P<season>\d+)'
```
