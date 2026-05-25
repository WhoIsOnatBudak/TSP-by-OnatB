CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -pedantic
CPPFLAGS ?= -Iinclude

TARGET := bin/tsp_aco
SWEEP_TARGET := bin/parameter_sweep
EVAPORATION_SWEEP_TARGET := bin/evaporation_sweep
COMMON_SOURCES := $(filter-out src/main.cpp src/parameter_sweep.cpp src/evaporation_sweep.cpp,$(wildcard src/*.cpp))
OBJECTS := $(patsubst src/%.cpp,build/%.o,$(COMMON_SOURCES) src/main.cpp)
SWEEP_OBJECTS := $(patsubst src/%.cpp,build/%.o,$(COMMON_SOURCES) src/parameter_sweep.cpp)
EVAPORATION_SWEEP_OBJECTS := $(patsubst src/%.cpp,build/%.o,$(COMMON_SOURCES) src/evaporation_sweep.cpp)

.PHONY: all run sweep evaporation-sweep clean

all: $(TARGET)

$(TARGET): $(OBJECTS) | bin
	$(CXX) $(CXXFLAGS) $(OBJECTS) -o $@

$(SWEEP_TARGET): $(SWEEP_OBJECTS) | bin
	$(CXX) $(CXXFLAGS) $(SWEEP_OBJECTS) -o $@

$(EVAPORATION_SWEEP_TARGET): $(EVAPORATION_SWEEP_OBJECTS) | bin
	$(CXX) $(CXXFLAGS) $(EVAPORATION_SWEEP_OBJECTS) -o $@

build/%.o: src/%.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

build bin:
	mkdir -p $@

run: $(TARGET)
	./$(TARGET)

sweep: $(SWEEP_TARGET)
	./$(SWEEP_TARGET)

evaporation-sweep: $(EVAPORATION_SWEEP_TARGET)
	./$(EVAPORATION_SWEEP_TARGET)

clean:
	rm -rf build bin output
