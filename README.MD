| Service name:PORT | Description                                                         |
|:------------------|:--------------------------------------------------------------------|
| **Service A :81** |	Catalog/Search Service  Fast reading, search, filters (CQRS Read Model).|
| **Service B :82** |	Inventory Service	CQRS Write Model. |
| **Service C :83** |	Order Service	Saga orcherstrator, manage orders.|
| **Service D :80** |	Auth Service	Authorization,gives JWT token, bind Telegram ID.|
| **Service E :84** |	Notification Service	Centralized sending notification (Telegram Bot).|


A - 81
B - 82
C - 83
D - 80
E - 84