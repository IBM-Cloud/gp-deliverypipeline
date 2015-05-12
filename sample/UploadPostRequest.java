/*
 *******************************************************************************
 *  IBM Globalization
 *  IBM Confidential / Copyright (C) IBM Corp. 2015 
 *******************************************************************************
 */
package com.ibm.gaas.requests;

import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

import org.json.JSONObject;

import com.ibm.gaas.services.TranslationProject;

public class UploadPostRequest extends RestfulRequest {
	
	TranslationProject project;
	boolean replace = true;
	boolean retry = false;

	public UploadPostRequest(TranslationProject job) {
		project = job;
	}
	
	public UploadPostRequest(TranslationProject job, boolean replace, boolean retry) {
		project = job;
		this.replace = replace;
		this.retry = retry;
	}
	
	public HttpURLConnection getConnection() throws Exception{
		HttpURLConnection connection = null;
		String urlPath = GAAS_URL_PROJECTS + project.getProjectID() + "/" + project.getLanguage();
		URL url = new URL(urlPath);
		connection = (HttpURLConnection) url.openConnection();
		connection.setDoOutput(true);
		connection.setDoInput(true);
		connection.setRequestProperty("accept", "*/*");
		connection.setRequestProperty("connection", "Keep-Alive");
		connection.setRequestMethod("POST");
		connection.setRequestProperty("api-key", project.getApiKey());
		connection.setRequestProperty("Content-Type", "application/json");
			
		JSONObject jsonBody = new JSONObject();
		if (project.getElements() != null) {
			jsonBody.put("data", project.getElements());
		}
		if (replace) {
			jsonBody.put("replace", replace);
		}
		if (retry) {
			jsonBody.put("retry", retry);
		}
	
		OutputStream os = connection.getOutputStream();
		PrintWriter pr = new PrintWriter(new OutputStreamWriter(os, StandardCharsets.UTF_8));
		pr.print(jsonBody.toString());
		pr.flush();
		return connection;
	}

	@Override
	public String getMsgResource() {
		return "UPDATE_RES";
	}

	@Override
	public int getExpectedRespCode() {
		return HttpURLConnection.HTTP_ACCEPTED;
	}
	
	
}
