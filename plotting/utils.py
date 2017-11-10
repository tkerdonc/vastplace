import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import multiprocessing


#This is mainly a wrapper around matplotlib functions, in order to spawn them into processes and avoid multithreading conflicts when plotting on the fly

def plotBarGraph_impl(return_dict, bars, xlabel, ylabel, legend):
	#plot the image and send it in the response
	plt.figure()
	for bar in bars:
		plt.bar(bar['X'], bar['Y'], label = bar['label'], width = bar['width'], color = bar['color'])
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	if legend:
		plt.legend()

	buf = io.BytesIO()
	plt.savefig(buf, format='svg')

	plt.close()
	buf.seek(0)

	return_dict['graph'] = buf

def plotBarGraph(bars, xlabel = "", ylabel = '', legend = False):
	manager = multiprocessing.Manager()
	return_dict = manager.dict()
	jobs = []
        p = multiprocessing.Process(target=plotBarGraph_impl, args=(return_dict, bars, xlabel, ylabel, legend))
        p.start()
       	p.join()

	return return_dict['graph']