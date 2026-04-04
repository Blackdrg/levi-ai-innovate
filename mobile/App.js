import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, ScrollView, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Brain, Send, Activity, ShieldCheck } from 'lucide-react-native';
import axios from 'axios';

// Sovereign API Endpoint (Default local dev)
const API_URL = "http://localhost:8000/api/v13/orchestrator/mission";

export default function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'LEVI-AI Sovereign Mobile Dashboard online. How can I assist you?' }
  ]);
  const [loading, setLoading] = useState(false);

  const startMission = async () => {
    if (!input.trim()) return;
    
    const userMsg = input;
    setMessages([...messages, { role: 'user', text: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(API_URL, {
        input: userMsg,
        session_id: "mobile_session_1"
      });

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: response.data.response || "Mission Synthesis Complete." 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', text: "Neural link unstable. Connect to Sovereign Node." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      
      {/* Sovereign Header */}
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <Brain color="#a855f7" size={24} />
          <Text style={styles.title}>LEVI-AI</Text>
        </View>
        <ShieldCheck color="#64748b" size={20} />
      </View>

      {/* Mission Stream */}
      <ScrollView style={styles.messagesList} contentContainerStyle={{ padding: 20 }}>
        {messages.map((m, i) => (
          <View key={i} style={[styles.bubble, m.role === 'user' ? styles.userBubble : styles.botBubble]}>
            <Text style={styles.bubbleText}>{m.text}</Text>
          </View>
        ))}
        {loading && (
          <View style={[styles.bubble, styles.botBubble]}>
            <Activity color="#a855f7" size={16} />
            <Text style={[styles.bubbleText, { marginLeft: 8 }]}>Sovereign Synthesis...</Text>
          </View>
        )}
      </ScrollView>

      {/* Input Module */}
      <View style={styles.inputArea}>
        <TextInput 
          style={styles.input}
          placeholder="Dispatch mission..."
          placeholderTextColor="#475569"
          value={input}
          onChangeText={setInput}
          onSubmitEditing={startMission}
        />
        <TouchableOpacity style={styles.sendButton} onPress={startMission}>
          <Send color="white" size={20} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#050507',
  },
  header: {
    padding: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    color: 'white',
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: -1,
    marginLeft: 10,
  },
  messagesList: {
    flex: 1,
  },
  bubble: {
    padding: 16,
    borderRadius: 20,
    marginBottom: 16,
    maxWidth: '85%',
  },
  userBubble: {
    backgroundColor: '#1e1b4b',
    alignSelf: 'flex-end',
    borderBottomRightRadius: 4,
  },
  botBubble: {
    backgroundColor: '#0f172a',
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderBottomColor: '#1e293b',
    flexDirection: 'row',
    alignItems: 'center',
  },
  bubbleText: {
    color: '#e2e8f0',
    fontSize: 15,
    lineHeight: 22,
  },
  inputArea: {
    padding: 20,
    flexDirection: 'row',
    gap: 12,
  },
  input: {
    flex: 1,
    backgroundColor: '#0f172a',
    borderRadius: 16,
    paddingHorizontal: 20,
    height: 56,
    color: 'white',
    borderWidth: 1,
    borderColor: '#1e293b',
  },
  sendButton: {
    width: 56,
    height: 56,
    backgroundColor: '#a855f7',
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  }
});
