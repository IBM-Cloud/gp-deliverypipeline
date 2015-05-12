/*
 *******************************************************************************
 *  IBM Globalization
 *  IBM Confidential / Copyright (C) IBM Corp. 2015 
 *******************************************************************************
 */
package com.ibm.gaas.ui;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.servlet.ServletException;
import javax.servlet.annotation.MultipartConfig;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.Part;

import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.mozilla.javascript.EvaluatorException;
import org.mozilla.javascript.Parser;
import org.mozilla.javascript.ast.AstRoot;

import com.ibm.gaas.requests.ConfigConstants;
import com.ibm.gaas.requests.ConfigReader;
import com.ibm.gaas.requests.GaasLogger;
import com.ibm.gaas.requests.RestCallException;
import com.ibm.gaas.requests.UploadPostRequest;
import com.ibm.gaas.services.APIKeyService;
import com.ibm.gaas.services.BomInputStream;
import com.ibm.gaas.services.LocaleService;
import com.ibm.gaas.services.TranslationProject;
import com.ibm.gaas.ui.g11n.G11NHelper;


/**
 * Servlet implementation class ResourceUploadServlet
 */

@WebServlet("/upload")
@MultipartConfig(fileSizeThreshold=1024*1024*2, // 2MB
				maxFileSize=1024*1024*1,      // 1MB
				maxRequestSize=1024*1024*1)   // 1MB
public class ResourceUploadServlet extends HttpServlet {
	
	private static final long serialVersionUID = 1L;
    
	private static GaasLogger logger = GaasLogger.getLogger(ResourceUploadServlet.class);
	
	private static final String RESOURCE_KEY_PATTERN = "^[a-zA-Z0-9_.-]+$";
	
	private Integer resMaxNum;
	private Integer resMaxKeySize;
	private Integer resMaxValueSize;
	
    /**
     * @see HttpServlet#HttpServlet()
     */
    public ResourceUploadServlet() {
        super();
        resMaxNum = ConfigReader.readConfigInteger(ConfigConstants.P_RES_MAX_NUM, 500);
        resMaxKeySize = ConfigReader.readConfigInteger(ConfigConstants.P_RES_MAX_KEY_SIZE, 256);
        resMaxValueSize = ConfigReader.readConfigInteger(ConfigConstants.P_RES_MAX_VALUE_SIZE, 2048);
    }

    // This gets the filename from the uploaded file
    private String getFileName(Part part) {
        for (String header : part.getHeader("content-disposition").split(";")) {
            if (header.trim().startsWith("filename")) {
                return header.substring(
                        header.indexOf('=') + 1).trim().replace("\"", "");
            }
        }
        return null;
    }
    
	/**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse response)
	 */
	protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse response)
	 * 
	 * This servlet responds to multipart/form-data
	 * You must supply: api-key, projectID, languageID, filetype, and file
	 * 
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		TranslationProject project = new TranslationProject();
		
		String locale = LocaleService.$.getCurrentLocale(request);
		G11NHelper h = G11NHelper.getHelper("upload_error.properties", locale);
		
		HashMap<String, String> pairs = new HashMap<String, String>();

		// Read all the parameters for the file upload request
		project.setApiKey(APIKeyService.$.getCurrentAPIKey(request));
		project.setLanguage(request.getParameter("languageID"));
		project.setProjectID(request.getParameter("projectID"));
		String fileType = request.getParameter("filetype");
		
		Part filePart = null;
		try {
			filePart = request.getPart("file");
		} catch (IllegalStateException e1) {
			UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, h.get("ERROR_TOO_LARGE_FILE"));
			return;
		}
		InputStream filecontent = filePart.getInputStream();
		String fileName = getFileName(filePart);
		
		logger.debug("start uploading " + fileName);
		
		if(fileType.equalsIgnoreCase("properties")) {
			try {
				Properties properties = new Properties();
				properties.load(filecontent);
				logger.debug("properties file " + fileName + " loaded");
				Enumeration<?> keys = properties.propertyNames();
				logger.debug("properties file " + fileName + " has " + properties.size() + " entries"); 
	        
				// Process all the keys in the Java property file
				while (keys.hasMoreElements()) {
					String key = (String) keys.nextElement();
					String value = properties.getProperty(key);
					value = new String(value.getBytes(StandardCharsets.UTF_8), StandardCharsets.UTF_8);
					pairs.put(key, value);
				}
			}
			// Tell the dashboard the request was bad
			catch(IOException | IllegalArgumentException e) {
				UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, h.get("ERROR_PARSE_PROPS"));
				return;
			}
		}
		else if(fileType.equalsIgnoreCase("json")) {
			try {
				JSONTokener tokens = new JSONTokener(new InputStreamReader(new BomInputStream(filecontent), StandardCharsets.UTF_8));
				logger.debug("json file " + fileName + " loaded");
				
				JSONObject json = new JSONObject(tokens);
				logger.debug("json file " + fileName + " has " + json.length() + " entries"); 
				// Process all the keys in the JSON object
	        	
	        	@SuppressWarnings("unchecked")
				Iterator<String> keys = json.keys();
	        	while(keys.hasNext()) {
	        		String key = (String)keys.next();
	        		pairs.put(key, json.getString(key));
	        	}
			}
			// Tell the dashboard the request was bad
			catch(JSONException e) {
				UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, h.get("ERROR_PARSE_JSON"));
				return;
			}
        	
        }
		else if(fileType.equalsIgnoreCase("js")) {
			try {
				InputStreamReader reader = new InputStreamReader(new BomInputStream(filecontent), StandardCharsets.UTF_8);
				AstRoot root = new Parser().parse(reader, fileName, 1);
				logger.debug("js file " + fileName + " loaded");
				KeyValueVisitor visitor = new KeyValueVisitor();
				root.visitAll(visitor);
				pairs = visitor.getElements();
				reader.close();
			}
			// Tell the dashboard the request was bad
			catch(EvaluatorException e) {
				UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, h.get("ERROR_PARSE_AMD_JS"));
				return;
			}
		}
		else {
			UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, h.get("ERROR_UNSUPPORTED_TYPE"));
			return;
		}
		
		if (pairs != null) {
			if (pairs.size() > resMaxNum) {
				UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, String.format(h.get("ERROR_EXCEED_MAX_PAIRS"), this.resMaxNum));
				return;
			}
			
			List<String>[] invalidKeys = validateKeys(pairs);
			if (invalidKeys != null) {
				List<String> invalidPatternKeys = invalidKeys[0];
				List<String> tooLongKeys = invalidKeys[1];
				
				if (invalidPatternKeys != null && invalidPatternKeys.size() > 0) {
					StringBuffer sb = new StringBuffer();
					this.composeListError(sb, h.get("ERROR_INVALID_KEY"), invalidPatternKeys);
					UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, sb.toString());
					return;
				}
				
				if (tooLongKeys != null && tooLongKeys.size() > 0) {
					StringBuffer sb = new StringBuffer();
					this.composeListError(sb, String.format(h.get("ERROR_EXCEED_MAX_KEY_LENGTH"), this.resMaxKeySize), tooLongKeys);
					UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, sb.toString());
					return;
				}
			}
			
			List<String> tooLongValueKeys = validateValues(pairs);
			if (tooLongValueKeys != null && tooLongValueKeys.size() > 0) {
				StringBuffer sb = new StringBuffer();
				this.composeListError(sb, String.format(h.get("ERROR_EXCEED_MAX_VALUE_LENGTH"), this.resMaxValueSize), tooLongValueKeys);
				UIServlet.sendError(response, HttpServletResponse.SC_BAD_REQUEST, sb.toString());
				return;
			}
		}
		
		/*
		 * No abnormal events occurred during the parsing of one of the 
		 * resource files.   
		 */
		
		if(!pairs.isEmpty()) {
			project.setElements(pairs);
			UploadPostRequest message = new UploadPostRequest(project);
			
			try {
				message.call(LocaleService.$.getCurrentLocale(request));
				// service call was successful
				response.setStatus(HttpServletResponse.SC_ACCEPTED);
			}
			// We encountered a serious problem calling the translation service
			catch(RestCallException e) {
				int code = e.getCode();
				String messageString = e.getMessage();
				UIServlet.sendError(response, code, messageString);
			}
		}
	}
	
	/**
	 * validate the keys, returns 2 lists of keys
	 * the 1st list contains all the keys that do not match the RESOURCE_KEY_PATTERN
	 * the 2st list contains all the keys that are too long
	 * @param elements
	 * @return 
	 */
	@SuppressWarnings("unchecked")
	private List<String>[] validateKeys(HashMap<String, String> elements) {
		List<String> invalidPatternKeys = new ArrayList<String>();
		List<String> tooLongKeys = new ArrayList<String>();
		
		if (elements != null) {
			Pattern p = Pattern.compile(RESOURCE_KEY_PATTERN);
			for (String key: elements.keySet()) {
				Matcher m = p.matcher(key);
				if (!m.matches()) {
					invalidPatternKeys.add(key);
				}
				if (key.length() > this.resMaxKeySize) {
					tooLongKeys.add(key);
				}
			}
		}
		
		return new List[] {invalidPatternKeys, tooLongKeys};
	}
	
	/**
	 * validate the values, returns the keys of which the value are too long
	 * @param elements
	 * @return 
	 */
	private List<String> validateValues(HashMap<String, String> elements) {
		List<String> invalidKeys = new ArrayList<String>();
		
		if (elements != null) {
			for (String key: elements.keySet()) {
				String value = elements.get(key);
				if (value.length() > this.resMaxValueSize) {
					invalidKeys.add(key);
				}
			}
		}
		
		return invalidKeys;
	}
	
	private void composeListError(StringBuffer sb, String message, List<String> keys) {
		sb.append(message);
		for (int i = 0; i < keys.size(); i++) {
			if (i > 0) {
				sb.append(", ");
			}
			sb.append(keys.get(i));
		}
	}
}
