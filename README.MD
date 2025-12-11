Service A	Catalog/Search Service  Fast reading, search, filters (CQRS Read Model).
Service B	Inventory Service	CQRS Write Model.
Service C	Order Service	Saga orcherstrator, manage orders.
Service D	Auth Service	Authorization,gives JWT token, bind Telegram ID.
Service E	Notification Service	Centralized sending notification (Telegram Bot).
WS Gateway	WebSocket Gateway Service	Manage websocket connect, Real-time monitoring.