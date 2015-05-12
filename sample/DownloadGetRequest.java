/*
 *******************************************************************************
 *  IBM Globalization
 *  IBM Confidential / Copyright (C) IBM Corp. 2015 
 *******************************************************************************
 */
package com.ibm.gaas.requests;


import java.net.HttpURLConnection;
import java.net.URL;

import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;

import com.ibm.gaas.services.TranslationProject;



public class DownloadGetRequest extends RestfulRequest {

	TranslationProject project;

	public DownloadGetRequest(TranslationProject job) {
		project = job;
	}
	
	public HttpURLConnection getConnection() throws Exception {
		HttpURLConnection connection = null;
		String urlPath = GAAS_URL_PROJECTS + project.getProjectID() + "/" + project.getLanguage();
		URL url = new URL(urlPath);
		connection = (HttpURLConnection) url.openConnection();
		connection.setDoOutput(true);
		connection.setRequestMethod("GET");
		connection.setRequestProperty("api-key", project.getApiKey());
		connection.setRequestProperty("Content-Type", "application/json");
		return connection;
	}

	@Override
	public String getMsgResource() {
		return "DOWNLOAD_RES";
	}

	@Override
	public int getExpectedRespCode() {
		return HttpURLConnection.HTTP_OK;
	}
	
	public JSONObject getTranslateResults(String locale) throws RestCallException, JSONException {
		String returnedString = this.call(locale);
		JSONObject jsonResponse = new JSONObject(new JSONTokener(returnedString));
	    JSONObject pairs = jsonResponse.getJSONObject("resourceData").getJSONObject("data");
	    return pairs;
	}
	
}
