CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -pedantic
CPPFLAGS ?= -Iinclude

TARGET := bin/tsp_aco
SOURCES := $(wildcard src/*.cpp)
OBJECTS := $(patsubst src/%.cpp,build/%.o,$(SOURCES))

.PHONY: all run clean

all: $(TARGET)

$(TARGET): $(OBJECTS) | bin
	$(CXX) $(CXXFLAGS) $(OBJECTS) -o $@

build/%.o: src/%.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

build bin:
	mkdir -p $@

run: $(TARGET)
	./$(TARGET)

clean:
	rm -rf build bin output
