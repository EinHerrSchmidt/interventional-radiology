from data_maker import DataDescriptor, DataMaker, TruncatedNormalParameters


def build_data_dictionary():
    dataDescriptor = DataDescriptor()
    dataDescriptor.patients = 80
    dataDescriptor.days = 5
    dataDescriptor.anesthetists = 2
    dataDescriptor.covidFrequence = 0.5
    dataDescriptor.anesthesiaFrequence = 0.5
    dataDescriptor.specialtyBalance = 0.17
    dataDescriptor.operatingDayDuration = 270
    dataDescriptor.anesthesiaTime = 270
    dataDescriptor.priorityDistribution = TruncatedNormalParameters(low=1,
                                                                    high=120,
                                                                    mean=60,
                                                                    stdDev=10)
    dataMaker = DataMaker(seed=52876)
    dataContainer = dataMaker.create_data_container(dataDescriptor)
    return dataMaker.create_data_dictionary(dataContainer, dataDescriptor)
