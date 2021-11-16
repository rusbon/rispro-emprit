package com.e205.empritmanager;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.snackbar.Snackbar;
import id.co.telkom.iot.AntaresHTTPAPI;
import id.co.telkom.iot.AntaresResponse;
import io.socket.client.IO;
import io.socket.client.Socket;
import io.socket.emitter.Emitter;
import org.eclipse.paho.android.service.MqttAndroidClient;
import org.eclipse.paho.client.mqttv3.*;
import org.json.JSONException;
import org.json.JSONObject;

import java.net.URI;

public class MainActivityOld extends AppCompatActivity implements AntaresHTTPAPI.OnResponseListener {

    private Button btnOn;
    private Button btnOff;
    private Button btnRefresh;
    private TextView socketStatus;
    private TextView isBirdDetected;
    private TextView motorState;
    private TextView controlMode;
    private LinearLayout indicatorBirdDetected;
    private LinearLayout indicatorBirdNotDetected;

//    Antares-HTTP
    private String TAG = "ANTARES-API";
    private AntaresHTTPAPI antaresAPIHTTP;
    private String dataDevice;
    private String antaresData;
    private String antaresControlMode = "Auto";
    private String antaresControlMotor = "";

//    Paho-MQTT
    MqttAndroidClient mqttAndroidClient;
    final String serverUri = "mqtt.antares.id:1883";
    String clientId = "android";
    final String subscriptionTopic = "/oneM2M/resp/antares-cse/c99552509917246b:5a8e2869cffd7e1c/json";
//    final String publishTopic = "exampleAndroidPublishTopic";
//    final String publishMessage = "Hello World!";

//    Socket Initialization
    private Socket mSocket;
    Handler handler;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        btnOn = (Button) findViewById(R.id.mqttOn);
        btnOff = (Button) findViewById(R.id.mqttOff);
        btnRefresh = (Button) findViewById(R.id.refresh);

        isBirdDetected = (TextView) findViewById(R.id.textView_is_bird_detected);
        motorState = (TextView) findViewById(R.id.textView_state_motor);
        controlMode = (TextView) findViewById(R.id.textView_control_mode);

        socketStatus = (TextView) findViewById(R.id.socketStatus);

        indicatorBirdDetected = (LinearLayout) findViewById(R.id.indicator_bird_detected);
        indicatorBirdNotDetected = (LinearLayout) findViewById(R.id.indicator_bird_not_detected);

        antaresAPIHTTP = new AntaresHTTPAPI();
        antaresAPIHTTP.addListener(this);

//        Get Latest Data
        antaresAPIHTTP.getLatestDataofDevice(
                "c99552509917246b:5a8e2869cffd7e1c",
                "Emprit",
                "android"
        );

        mqttAndroidClient = new MqttAndroidClient(getApplicationContext(), serverUri, clientId);
        mqttAndroidClient.setCallback(new MqttCallbackExtended() {
            @Override
            public void connectComplete(boolean reconnect, String serverURI) {

                if (reconnect) {
                    addToHistory("Reconnected to : " + serverURI);
                    // Because Clean Session is true, we need to re-subscribe
                    subscribeToTopic();
                } else {
                    addToHistory("Connected to: " + serverURI);
                }
            }

            @Override
            public void connectionLost(Throwable cause) {
                addToHistory("The Connection was lost.");
            }

            @Override
            public void messageArrived(String topic, MqttMessage message) throws Exception {
                addToHistory("Incoming message: " + new String(message.getPayload()));
            }

            @Override
            public void deliveryComplete(IMqttDeliveryToken token) {

            }
        });

//        Initializing Socket
        URI uri = URI.create("http://10.124.4.111:5000");
        IO.Options options = IO.Options.builder()
                .build();
        mSocket = IO.socket(uri, options);

        mSocket.on(Socket.EVENT_CONNECT, new Emitter.Listener() {
            @Override
            public void call(Object... args) {
                System.out.println("LOG: " + "Connected");
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        socketStatus.setText("ON");
                    }
                });
            }
        });

        mSocket.on(Socket.EVENT_CONNECT_ERROR, new Emitter.Listener() {
            @Override
            public void call(Object... args) {
                System.out.println("LOG: " + "Connection Error");
            }
        });

        mSocket.on(Socket.EVENT_DISCONNECT, new Emitter.Listener() {
            @Override
            public void call(Object... args) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        socketStatus.setText("OFF");
                    }
                });
            }
        });
        mSocket.on("hello", new Emitter.Listener() {
            @Override
            public void call(Object... args) {
                System.out.println(args[0]); // world
            }
        });

//        Set Timer to update data from antares
        handler = new Handler(Looper.getMainLooper());
        Runnable runnable = new Runnable() {

            @Override
            public void run() {
                try{
                    antares_refresh();
                }
                catch (Exception e) {
                    // TODO: handle exception
                }
                finally{
                    //also call the same runnable to call it at regular interval
                    handler.postDelayed(this, 500);
                }
            }
        };
        handler.post(runnable);

    }

    public void btn_toggle_click(View v){
        if (antaresControlMode.equals("Auto")){
            antaresControlMode = "Manual";
        }
        else if (antaresControlMode.equals("Manual")){
            antaresControlMode = "Auto";
        }
        antares_send();
    }

    public void btn_on_click(View v){
        antaresControlMotor = "1";
        antares_send();
    }

    public void btn_off_click(View v){
        antaresControlMotor = "0";
        antares_send();
    }

    private void antares_send(){
        Log.d(TAG, "Sending Data");
        antaresData = "{" +
                "\\\"android\\\": {" +
                    "\\\"mode\\\":\\\"" + antaresControlMode + "\\\"" +
                    "," +
                    "\\\"control_motor\\\":\\\"" + antaresControlMotor + "\\\"" +
                    "}" +
                "}";

        antaresAPIHTTP.storeDataofDevice(
                1,
                "c99552509917246b:5a8e2869cffd7e1c",
                "Emprit",
                "android",
                antaresData
        );
    }

    public void btn_refresh_click(View v){
        antares_refresh();
    }

    private void antares_refresh(){
        antaresAPIHTTP.getLatestDataofDevice(
                "c99552509917246b:5a8e2869cffd7e1c",
                "Emprit",
                "android"
        );
        antaresAPIHTTP.getLatestDataofDevice(
                "c99552509917246b:5a8e2869cffd7e1c",
                "Emprit",
                "jetson"
        );
    }

    public void btn_socket_connect_click(View v){
        if (!mSocket.isActive()){
            System.out.println("LOG: " + "Connecting");
            mSocket.connect();
        }else{
            mSocket.disconnect();
        }
    }

    public void btn_socket_on_click(View v){
        if (mSocket.isActive()){
            mSocket.emit("control", "on");
        }
    }

    public void btn_socket_off_click(View v){
        if (mSocket.isActive()){
            mSocket.emit("control", "off");
        }
    }

    private void addToHistory(String mainText){
        System.out.println("LOG: " + mainText);
        Snackbar.make(findViewById(android.R.id.content), mainText, Snackbar.LENGTH_LONG)
                .setAction("Action", null).show();

    }

    @Override
    public void onResponse(AntaresResponse antaresResponse) {
        Log.d(TAG,Integer.toString(antaresResponse.getRequestCode()));
        if(antaresResponse.getRequestCode()==0){
            try {
                JSONObject body = new JSONObject(antaresResponse.getBody());
                String data = body.getJSONObject("m2m:cin").getString("con");

                if (data.contains("android")){
                    JSONObject data_android = new JSONObject(data).getJSONObject("android");

                    antaresControlMode = data_android.getString("mode");
                    antaresControlMotor = data_android.getString("control_motor");

                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            motorState.setText(antaresControlMotor);
                            controlMode.setText(antaresControlMode);
                        }
                    });
                }
                if (data.contains("jetson")){
                    JSONObject data_android = new JSONObject(data).getJSONObject("jetson");

                    dataDevice = data_android.getString("burung_terdeteksi");

                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            isBirdDetected.setText(dataDevice);
                            if (dataDevice.equals("true")){
                                indicatorBirdDetected.setVisibility(View.VISIBLE);
                                indicatorBirdNotDetected.setVisibility(View.GONE);
                            }
                            if (dataDevice.equals("false")){
                                indicatorBirdDetected.setVisibility(View.GONE);
                                indicatorBirdNotDetected.setVisibility(View.VISIBLE);
                            }
                        }
                    });
                }

//                dataDevice = data.getString("burung_terdeteksi");
//                Log.d(TAG,antaresResponse.getBody());
            } catch (JSONException e) {
                e.printStackTrace();
            }
        }
    }

    public void subscribeToTopic(){
        try {
            mqttAndroidClient.subscribe(subscriptionTopic, 0, null, new IMqttActionListener() {
                @Override
                public void onSuccess(IMqttToken asyncActionToken) {
                    addToHistory("Subscribed!");
                }

                @Override
                public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
                    addToHistory("Failed to subscribe");
                }
            });

        } catch (MqttException ex){
            System.err.println("Exception whilst subscribing");
            ex.printStackTrace();
        }
    }
}