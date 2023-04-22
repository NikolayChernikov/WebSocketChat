html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your nickname: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <h2>Change nickname: <span id="ws-id"></span></h2>
        <form action="" onsubmit="setNickname(event)">
            <input type="text" id="messageText1" autocomplete="off"/>
            <button>Send</button>
        </form>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                var client = document.querySelector("#ws-id").textContent
                ws.send([client,input.value])
                input.value = ''
                event.preventDefault()
            }
            function setNickname(event) {
                var input = document.getElementById("messageText1")
                document.querySelector("#ws-id").textContent = input.value;
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""