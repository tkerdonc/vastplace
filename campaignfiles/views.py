# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotFound

from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS, GridFSBucket

from forms import UploadFileForm
from models import SourceType

def index(request):
    return HttpResponse("Nothing to see here yet.")

def upload_file(request):
    response = None
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
	    fileId = handle_uploaded_file(request.FILES['file'])
	    #t = threading.Thread(target=handle_uploaded_file, args = ([request.FILES['file']]))
	    #t.start()
            response = HttpResponseRedirect('/campaignfiles/details/' + str(fileId))
    else:
            response = HttpResponseRedirect('/campaignfiles/content')

    return response

def handle_uploaded_file(inputFile):
	client = MongoClient()
	db = client.trace_database
	fs = GridFSBucket(db)
	
	grid_in = fs.open_upload_stream(str(inputFile), metadata={"source_processed":0})
	for ch in  inputFile.chunks():
		grid_in.write(ch)
	grid_in.close() 

	return ObjectId(grid_in._id)

def stored_files(request):
	client = MongoClient()
	db = client.trace_database
	return render(request, 'campaignfiles/content.html', {'fileList': [{'id':f['_id'], "filename":f["filename"], "length":f["length"]} for f in db.fs.files.find()]})

def download(request, fileId):
	client = MongoClient()
	db = client.trace_database
	fs = GridFS(db)
	if fs.exists(_id=ObjectId(fileId)):
		retfile = fs.get(ObjectId(fileId))
		response = HttpResponse(retfile)
		response['Content-Disposition'] = 'attachment; filename="' + retfile.filename + '"'
		return response
	else:
		raise HttpResponseNotFound('<h1>File not found</h1>')

def delete(request, fileId):
	client = MongoClient()
	db = client.trace_database
	fs = GridFS(db)
	if fs.exists(_id=ObjectId(fileId)):
		fs.delete(ObjectId(fileId))

	point_db = client.point_database
	point_db.sensors.delete_many({"sourceId":fileId})
	point_db.wifiscanresults.delete_many({"sourceId":fileId})
		
        return HttpResponseRedirect('/campaignfiles/content')



def viewdetails(request, fileId):
	responseData = {'id':fileId}

	client = MongoClient()
	db = client.trace_database
	fs = GridFS(db)
	traceFile = fs.get(ObjectId(fileId))

	for k in ['phoneuser', 'phoneId', 'notes']:
		if k in traceFile.metadata:
			responseData[k] = traceFile.metadata[k]

	responseData['sourceTypes']= []
	enabled_types = []
	if 'sourceTypes' in traceFile.metadata:
		enabled_types = traceFile.metadata['sourceTypes']

	all_types = SourceType.objects.values_list('sourceType', flat = True)
	for t in all_types:
		if t in enabled_types:
			responseData['sourceTypes'].append({'name':t, 'enabled':"checked"})
		else:
			responseData['sourceTypes'].append({'name':t, 'enabled':''})

	return render(request, 'campaignfiles/details.html', responseData)



def edit(request, fileId):
	client = MongoClient()
	db = client.trace_database
	

	for k in ['phoneuser', 'phoneId', 'notes']:
		db.fs.files.update_one({'_id': ObjectId(fileId)}, {'$set': {'metadata.' + k: request.POST[k]}})
	
	types = SourceType.objects.values_list('sourceType', flat = True)
	enabled_types = []
	for t in types:
		if t in request.POST and 'on' in request.POST[t]:
			enabled_types.append(t)


	db.fs.files.update_one({'_id': ObjectId(fileId)}, {'$set': {'metadata.sourceTypes' : enabled_types}})

        #return HttpResponseRedirect('/campaignfiles/content')
	return viewdetails(request, fileId)


